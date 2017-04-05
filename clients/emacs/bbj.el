(require 'json)
(require 'url)
(require 'shr)
(require 'cl)

(defvar bbj-host "127.0.0.1")
(defvar bbj-port 8080)
(defvar bbj-width 80)

(defvar bbj-user "anonymous"
  "The username of the currently logged in user. The value of this
variable is irrelevant if `bbj-hash' is not set as well")

(defvar bbj-hash nil
  "The sha256 authorization hash of the currently logged in user. May
be nil to use BBJ as an anon.")

(defvar bbj-noheaders nil
  "When non-nil, will not send headers with a request even if user and
hash are set")

(defvar bbj-debug nil
  "When non-nil, bbj will command emacs will do fairly intrusive and
obnoxious things for the sake of education ;)")

(defvar bbj-old-p (eq emacs-major-version 24))
(make-variable-buffer-local
 (defvar bbj-refresh-timer nil))
(make-variable-buffer-local
 (defvar bbj-*usermap* nil))
(make-variable-buffer-local
 (defvar bbj-buffer-type nil))
(make-variable-buffer-local
 (defvar bbj-aux-callback #'ignore))

(define-derived-mode bbj-mode fundamental-mode "BBJ"
  "Mode for browsing and posting to BBJ."
  :group 'bbj-mode
  (local-set-key (kbd "SPC")     'bbj-next-post)
  (local-set-key (kbd "j")       'bbj-next-post)
  (local-set-key (kbd "n")       'bbj-next-post)
  (local-set-key (kbd "<down>")  'bbj-next-post)

  (local-set-key (kbd "DEL")     'bbj-prev-post)
  (local-set-key (kbd "k")       'bbj-prev-post)
  (local-set-key (kbd "p")       'bbj-prev-post)
  (local-set-key (kbd "<up>")    'bbj-prev-post)

  (local-set-key (kbd "g")       'bbj-refresh)
  (local-set-key (kbd "<f5>")    'bbj-refresh)

  (local-set-key (kbd "J")       'scroll-up-line)
  (local-set-key (kbd "N")       'scroll-up-line)
  (local-set-key (kbd "S-SPC")   'scroll-up-line)
  (local-set-key (kbd "<S-down>")'scroll-up-line)

  (local-set-key (kbd "K")       'scroll-down-line)
  (local-set-key (kbd "P")       'scroll-down-line)
  (local-set-key (kbd "<S-up>")  'scroll-down-line)
  (local-set-key (kbd "<S-backspace>") 'scroll-down-line)

  (local-set-key (kbd "RET")     'bbj-enter)
  (local-set-key (kbd "l")       'bbj-enter)
  (local-set-key (kbd "o")       'bbj-enter)
  (local-set-key (kbd "<right>") 'bbj-enter)

  (local-set-key (kbd "q")       'quit-window)
  (local-set-key (kbd "<left>")  'quit-window)
  (local-set-key (kbd "<escape>")'quit-window)

  (local-set-key (kbd "+")       'bbj-compose)
  (local-set-key (kbd "c")       'bbj-compose)

  (local-set-key (kbd "C-h SPC") 'bbj-pop-help)
  (local-set-key (kbd "?")       'bbj-pop-help)
  (local-set-key (kbd "e")       'bbj-edit-post)
  (local-set-key (kbd "C-c C-c") 'bbj-aux)
  (local-set-key (kbd "r")       'bbj-quote-current-post))

(ignore-errors
  (evil-set-initial-state 'bbj-mode 'emacs))

;;;; shit to put up with outdated emacs on the tilde ;;;;

(when bbj-old-p

  (defun alist-get (key alist &optional default remove)
    (ignore remove) ;;Silence byte-compiler.
    (let ((x (assq key alist)))
      (if x (cdr x) default)))

  (defsubst string-trim-left (string)
    "Remove leading whitespace from STRING."
    (if (string-match "\\`[ \t\n\r]+" string)
        (replace-match "" t t string)
      string))

  (defsubst string-trim-right (string)
    "Remove trailing whitespace from STRING."
    (if (string-match "[ \t\n\r]+\\'" string)
        (replace-match "" t t string)
      string))

  (defsubst string-trim (string)
    "Remove leading and trailing whitespace from STRING."
    (string-trim-left (string-trim-right string))))


(cl-defun bbj-request (endpoint &rest params &aux alist)
  "Send an http request to the BBJ api. PARAMS can be pairs, where the
first element of each is a string key and the second is an object value,
or can be ommitted to send no data."
  (declare (indent 1))
  (while params
    (push (cons (format "%s" (pop params)) (pop params)) alist))

  (let* (json-false json-null json error edesc ecode
         (url-request-extra-headers
          (append
           '(("Content-Length" . "0"))
           (when (and (not bbj-noheaders) bbj-user bbj-hash)
            `(("User" . ,bbj-user) ("Auth" . ,bbj-hash)))))
         (url-request-method "POST")
         (url-request-data
          (when alist (json-encode-alist alist)))
         (response (url-retrieve-synchronously
           (format "http://%s:%s/api/%s" bbj-host bbj-port endpoint) t)))

    (when bbj-debug
      (switch-to-buffer response))

    (with-current-buffer response
      (goto-char (point-min))
      (re-search-forward "^$" nil t)
      (condition-case nil
          (setq json (json-read))
        (error
         (user-error "BBJ response error"))))

    (case (setq error (alist-get 'error json)
                edesc (alist-get 'description error)
                ecode (alist-get 'code error))
      ((0 1 2 3) (error edesc))
      ((4) (user-error edesc))
      ((5) (signal 'bbj-auth-error edesc))
      (otherwise json))))


(defun bbj-request! (&rest args)
  "same as `bbj-request' but the data key of the response
is the only thing returned (not the usermap or error field)"
  (declare (indent 1))
  (bbj-data (apply #'bbj-request args)))


(defun bbj-sane-value (prompt key)
  "Opens an input loop with the user, where the response is
passed to the server to check it for validity before the
user is allowed to continue. Will recurse until the input
is valid, then it is returned."
  (let (response value)
    (setq value (read-from-minibuffer prompt)
          response (bbj-request! 'db_sanity_check
                     'value value
                     'key key))
    (if (alist-get 'bool response)
        value
      (message (alist-get 'description response))
      (sit-for 2)
      (bbj-sane-value prompt key))))


(defun bbj-descend (alist &rest keys)
  "Recursively retrieve symbols from a nested alist. A required beverage
for all JSON tourists."
  (while keys
    (setq alist (alist-get (pop keys) alist)))
  alist)


(defun bbj-data (response)
  "Simply return the value of a response's data"
  (declare (indent 0))
  (alist-get 'data response))


(defun bbj-login ()
  "Prompts the user for a name and password. If it isn't registered, we'll take
care of that. This function only needs to be used once per emacs session.

You can restore anon status on demand by using `bbj-logout'"
  (interactive)
  (let ((bbj-noheaders t) check done)
    (setq bbj-user
          (bbj-sane-value
           "(BBJ Username)> "
           "user_name"))
    (cond
     ((bbj-request! 'user_is_registered 'target_user bbj-user)
      (if (bbj-request! 'check_auth
            'target_user bbj-user
            'target_hash (bbj-sethash))
          (message "Logged in as %s!" bbj-user)
        (setq bbj-hash nil)
        (if (y-or-n-p (format "Invalid credentials for %s. Try again? " bbj-user))
            (bbj-login)
          (setq bbj-user nil))))

     ((y-or-n-p (format "Register for BBJ as %s? " bbj-user))
      (while (not done)
        (condition-case error-response
            (let* ((init (bbj-sethash
                     (format "(Select a password for %s)> " bbj-user)))
                   (conf (bbj-sethash
                          (if (equal init (secure-hash 'sha256 ""))
                              "(Confirm empty password)> "
                            "(Confirm it)> "))))
              (unless (equal init conf)
                (error "Passwords do not match."))
              (bbj-request 'user_register
                'user_name bbj-user
                'auth_hash bbj-hash)
              (message "Registered and logged in as %s!" bbj-user)
              (setq done t))
          (error
           (unless (y-or-n-p (format "%s Try again? " (cadr error-response)))
             (setq done t
                   bbj-user nil
                   bbj-hash nil)))))))))


(defun bbj-logout (&optional nomessage)
  "Sets the user data back to nil so you can use BBJ as an anon"
  (interactive)
  (unless nomessage
    (message "You're now set as an anon."))
  (setq bbj-user "anonymous"
        bbj-hash nil))


(defun bbj-sethash (&optional prompt)
  "Prompts the user for a password and then sha256 hashes it.
Sets it globally and also returns it."
  (setq bbj-hash
    (secure-hash 'sha256 (read-from-minibuffer
      (or prompt "(Password)> ")))))


;;;; user navigation shit. a LOT of user navigation shit. ;;;;
(defun bbj-next-pos (string &optional regex prop backward group bound)
  ;; haha yes i ripped this from one of my other projects
  "Takes a STRING and returns the char position of the beginning of its
next occurence from point in `current-buffer'. Returns nil if not found.
A simpler way to call this is to use `bbj-next-prop'.

When REGEX is non-nil, STRING is interpreted as a regular expression.

PROP, when non-nil, will only return matches if they have the corresponding
value for a property.  This can either be a symbol or a cons cell. If it's
a symbol, the property key used is 'type. As a cons, The key and expected
value are given, eg '(type . end)

BACKWARD, when non-nil, does what it says on the tin.

When GROUP is non-nil and an integer, returns start pos of that match
group. When PROP is in effect, it checks property at this position instead
of 0.

BOUND can be a buffer position (integer) that the search will not exceed."
  (save-excursion
    (let ((search (if backward (if regex 're-search-backward 'search-backward)
                    (if regex 're-search-forward 'search-forward)))
          (group (or group 0))
          (propkey (if (consp prop) (car prop) 'type))
          (propval (if (consp prop) (cdr prop) prop))
          found)
      (while (and (not found) (funcall search string bound t))
        (if prop (setq found
            (eql propval (get-char-property
              (match-beginning group) propkey)))
          (setq found t)))
      (when found
        (match-beginning group)))))


(defun bbj-next-prop (prop &optional backward bound)
  "Like the `bbj-next-pos', but doesnt care about strings and
just hunts for a specific text property."
  (bbj-next-pos "." t prop backward nil bound))


(defun bbj-post-prop (prop &optional id)
  "retrieve PROP from the current post. needs ID-seeking support"
  (save-excursion
    (bbj-assert-post-start)
    (get-char-property (point) prop)))


;; returns positions of the next head and ending seps, respectively
(defun bbj-head-pos (&optional backward)
  (bbj-next-prop 'head backward))
(defun bbj-sep-pos (&optional backward)
  (bbj-next-prop 'end backward))


(defun bbj-assert-post-start ()
  (unless (eql 'head (get-char-property (point) 'type))
    (goto-char (bbj-head-pos t))))


(defun bbj-point-to-post (dir &optional nocenter)
  "Move the cursor from the head of one post to another, in (symbol) DIR"
  (let ((check (case dir
          (prev (bbj-head-pos t))
          (next (save-excursion ;; or else point will stick
                   (while (eq 'head (get-char-property (point) 'type))
                     (goto-char (next-property-change (point))))
                   (bbj-head-pos))))))
    (when check
      (goto-char check)
      (back-to-indentation)
      (unless nocenter (recenter 1)))))


(defun bbj-next-post ()
  (interactive)
  (bbj-point-to-post 'next))


(defun bbj-prev-post ()
  (interactive)
  (bbj-point-to-post 'prev))


(defun bbj-first-post ()
  (interactive)
  (goto-char (+ 1 bbj-width (point-min))))


(defun bbj-seek-post (id)
  "Locate a post number and jump to it."
  (let (p1 p2)
    (when (eq bbj-buffer-type 'thread)
      (if (member id '("0" 0))
          (bbj-first-post)
        (setq p1 (point))
        (goto-char (point-min))
        (when (not (setq p2
            (bbj-next-pos (format ">>%s " id) nil 'head)))
          (message "post %s not found" id))
        (goto-char (or p2 p1))
        (recenter t)))))


(defun bbj-aux ()
  "just some random lazy callback shitty thing for C-c C-c"
  (interactive)
  (funcall bbj-aux-callback))


(defun bbj-enter ()
  "Handles the RETURN key (and other similar binds) depending on
content type. Currently only opens threads."
  (interactive)
  (case bbj-buffer-type
    (index
     (bbj-enter-thread
      (alist-get 'thread_id (bbj-post-prop 'data))))))


(defun bbj-quote-current-post ()
  "Pop a composer, and insert the post number at point as a quote."
  (interactive)
  (case bbj-buffer-type
    (thread
     (let ((id (alist-get 'post_id (bbj-post-prop 'data))))
       (bbj-compose)
       (insert (format ">>%s\n\n" id))))
    (index
     ;; recursion haha yes
     (let ((buffer (current-buffer)))
       (bbj-enter)
       (unless (equal buffer (current-buffer))
         (bbj-quote-current-post))))))


(defun bbj-compose ()
  "Construct an appropriate callback to either create a thread or
reply to one. Pops a new window; window is killed and the message
is sent using C-c C-c."
  (interactive)
  (let ((params (case bbj-buffer-type
     (index
      `("Composing a new thread (C-c C-c to send)"
        (lambda ()
          (let* ((message (bbj-consume-window (current-buffer)))
                 (request (bbj-request 'thread_create
                   'body message
                   'title ,(bbj-sane-value "(Title)> " "title"))))
            (bbj-browse-index)
            (message "thread submitted")))))
     (thread
      `("Replying to thread (C-c C-c to send)"
        (lambda ()
          (let* ((message (bbj-consume-window (current-buffer)))
                 (request (bbj-request 'thread_reply
                            'body message 'thread_id ,thread-id)))
            (message "reply submitted")
            (bbj-enter-thread ,thread-id)
            (goto-char (point-max))
            (bbj-point-to-post 'prev)
            (recenter nil))))))))

    (apply #'bbj-compose-in-window params)))


(defun bbj-compose-in-window (title callback &rest cbargs)
  "Create a new buffer, pop it, set TITLE as the header line, and
assign CALLBACK to C-c C-c."
  (let ((buffer (get-buffer-create "BBJ: Compose")))
    (pop-to-buffer buffer)
    (with-current-buffer buffer
      (erase-buffer)
      (text-mode)
      (use-local-map (copy-keymap text-mode-map))
      (local-set-key (kbd "C-c C-c") 'bbj-aux)
      (setq header-line-format title
            bbj-aux-callback callback))))


(defun bbj-consume-window (buffer)
  "Consume all text in the current buffer, delete the window if
it is one, and kill the buffer. Returns property-free string."
  (with-current-buffer buffer
    (let ((content (buffer-substring-no-properties
                    (point-min) (point-max))))
      (quit-window t)
      content)))


;; rendering shit

(defun bbj-postprocess ()
  "Makes all the whitespace in and between posts consistent."
  (bbj-first-post)
  (save-excursion
    (while (re-search-forward "\n\n\n+" nil t)
      (replace-match "\n\n"))))


(defun bbj-render-body (string &optional return-string notrim)
  "takes an html STRING. If RETURN-STRING is non nil, it renders
it in a temp buffer and returns the string. Otherwise, inserts
and renders the content in the current buffer."
  (let* ((shr-width bbj-width)
         (shr-external-rendering-functions
          '((span . bbj-render-tag-span)))
         result)
    (if (not return-string)
        (let ((start (point)))
          (insert string)
          (shr-render-region start (point-max))
          (insert "\n\n"))
      (setq result
            (with-temp-buffer
              (insert string)
              (shr-render-region (point-min) (point-max))
              (buffer-substring (point-min) (point-max))))
      (if notrim result (string-trim result)))))


(defun bbj-timestring (epoch)
  "Make a cute timestring out of the epoch (for post heads)"
  (format-time-string "%H:%M %a %m/%d/%y" (seconds-to-time epoch)))


(defun bbj-render-post (post)
  "Render an API post object into the current buffer."
  (let* ((title (alist-get 'title post))
         (post-id (alist-get 'post_id post))
         (userdata (cdr (assoc-string (alist-get 'author post) bbj-*usermap*)))
         (indicator (format ">>%s " (or title post-id))))
    (insert (propertize indicator
      'face 'font-lock-function-name-face
      'type 'head 'data post))
    (when title (insert "\n"))
    (insert (propertize
      (concat "~" (alist-get 'user_name userdata) " ")
      'face 'font-lock-keyword-face))
    (insert (if (eq bbj-buffer-type 'index)
        (propertize (format "@ %s\n%s replies; last active %s\n"
            (bbj-timestring (alist-get 'created post))
            (alist-get 'reply_count post)
            (bbj-timestring (alist-get 'last_mod post)))
          'face 'font-lock-comment-face)
      (propertize (format "@ %s\n\n" (bbj-timestring (alist-get 'created post)))
        'face 'font-lock-comment-face)))
    (unless title
      (let ((p (point))
            (fill-column (min bbj-width (window-width))))
        (insert (alist-get 'body post))
        (fill-region p (point))))
    (insert "\n")
    ;; (bbj-render-body (alist-get 'body post))
    (bbj-insert-sep)))


(defun bbj-render-tag-span (dom)
  "A highly bastardized version of e25's `shr-tag-span', beaten and
maimed until it worked on emacs 24."
  (let ((class (if bbj-old-p
                   (alist-get :class dom)
                 (dom-attr dom 'class)))
        (text (if bbj-old-p
                  (alist-get 'text dom)
                (car (last dom)))))
    (cond
     ((equal class "quote")
      (insert (propertize text
               'face 'font-lock-constant-face
               'type 'quote)))
     ((equal class "linequote")
      (unless (bolp) (insert "\n"))
      (insert (propertize text
               'face 'font-lock-string-face
               'type 'linequote)))
     (t (shr-generic dom)))))


(defun bbj-mksep ()
  (format "\n%s\n" (make-string bbj-width ?\-)))


(defun bbj-insert-sep (&optional drop-newline)
  (let ((sep (bbj-mksep)))
    (insert (propertize
      (if drop-newline (subseq sep 1) sep)
      'face 'font-lock-comment-face
      'type 'end))))


(defun bbj-pop-help ()
  "Displays the help text."
  (interactive)
  ;; yes lets embed this shit in the source code haha epic
  (let ((help "hi this is help pleased to meet ye 8)

Please note the keys described below apply to thread and index buffers,
not this help page.

n, j, down arrow, and spacebar all move down by a whole post.
p, k, up arrow, and backspace go up, again by a whole post.

for n/p/j/k, hold shift (or use caps lock if you're into that) to scroll up or
down by one exactly one line. You can also use shift with the arrow keys, and
space/backspace, but if you are using terminal emacs, your terminal emulator may
not work properly with these combos.

The normal emacs paging and cursor movement keys (besides arrows) are not
affected, if you are already familiar with them. C-n goes down a line, C-p goes
up, C-v pages down, M-v pages up. (reminder: M means alt here in Emacs lala
land) The keyboard's dedicated paging keys will work too.

Open a thread with enter, or the o key.

The make-a-post keys are c and + (the plus key). If you are in the index, it
will make a new thread and prompt you at the minibuffer for a title and some
tags. If you dont want tags, just press enter again. If you're in a thread, this
will begin composing a new reply.

In the composure window, press control-c twice to fire it off to the server. If
you would like to discard the post, you can kill or hide this buffer using the
standard emacs keys. C-x 4 0 will kill the buffer and the window. C-x 0 will
just hide the window. C-x k RET will kill the buffer but not the window.

In addition to the composure keys, r is bound to insert a quote element for the
post at point after popping a reply window. Post quotes look like >>32, that is,
they are two angle brackets pointing at a number. They currently dont do
anything special. Later versions of the client will support navigation features
using them. r is not required to use these: you can also type them in yourself.

Pressing e on a post will pop a new window to edit it, given that the post is
yours and is not older than 24 hours. Currently this returns the html-rendered
output of the markdown parser, which is quite clunky and i will fix that. But
pressing C-c C-c will update it for everyone with the new data.

g or f5 will reload whatever buffer you are in, thread or index. If you are in a
thread, it will save whatever post your cursor is positioned at. Use this to
check for new messages.

q will get out of a thread and back to the index. If you're on the index, it
will kill that too. If you've killed the index, you can get back using the
command alt+x bbj-browse-index (tab completion is available)

The command names to log in, and browse to the index are bbj-login and
bbj-browse-index respectively.

Thats about it for now.
"))
    (let ((buffer (get-buffer-create "BBJ: Help"))
          (inhibit-read-only t))
      (with-current-buffer buffer
          (erase-buffer)
        (insert help)
        (goto-char (point-min))
        (text-mode)
        (use-local-map (copy-keymap text-mode-map))
        (local-set-key (kbd "q") 'kill-buffer-and-window)
        (setq header-line-format
              "Press q or C-x 4 0 to get out. Arrows can scroll."
              buffer-read-only t))
      (pop-to-buffer buffer)
      (ignore-errors
        (evil-emacs-state)))))


(defun bbj-refresh ()
  "Reload current buffer. Tries to keep point position in threads."
  (interactive)
  (case bbj-buffer-type
    (index
     (let ((point (point)))
       (bbj-browse-index)
       (goto-char point)
       (recenter t)))
    (thread
     (let ((post (alist-get 'post_id (bbj-post-prop 'data))))
       (bbj-enter-thread thread-id)
       (bbj-seek-post post)))))


(defun bbj-edit-post ()
  (interactive)
  (when (eq bbj-buffer-type 'index)
    (let ((buffer (current-buffer)))
      (bbj-enter)
      (unless (eql buffer (current-buffer))
        (bbj-edit-post))))

  (let* ((post-id (alist-get 'post_id (bbj-post-prop 'data)))
         (query (bbj-request! 'edit_query 'post_id post-id 'thread_id thread-id))
         (body (alist-get 'body query))
         (callback
          `(lambda ()
             (let* ((message (bbj-consume-window (current-buffer)))
                    (request
                     (bbj-request! 'edit_post
                       'post_id ,post-id
                       'thread_id ,thread-id
                       'body message)))
               (message "post edited")
               (bbj-enter-thread ,thread-id)
               (bbj-seek-post ,post-id)))))

    (bbj-compose-in-window "Editing post (including html) (C-c C-c to send)" callback)
    (insert body)
    (goto-char (point-min))))


(defun bbj-browse-index ()
  (interactive)
  (let* ((inhibit-read-only t)
         (buffer (get-buffer-create "BBJ Index"))
         (response (bbj-request 'thread_index))
         (count 0))
    (with-current-buffer buffer
      (erase-buffer)
      (bbj-mode)
      (setq bbj-buffer-type 'index
            bbj-*usermap* (alist-get 'usermap response)
            mode-line-process '(":~%e" bbj-user))
      (bbj-insert-sep t)
      (loop for thread across (alist-get 'data response) do
            (bbj-render-post thread)
            (incf count))
      (bbj-postprocess)
      (setq header-line-format (format
            "%d posts. g to refresh. Control+h then spacebar for help."
            count)))
    (switch-to-buffer buffer)
    (setq buffer-read-only t)))


(defalias 'bbj-index #'bbj-browse-index)


(defun bbj-enter-thread (id)
  (interactive)
  (let* ((inhibit-read-only t)
         (response (bbj-request 'thread_load 'thread_id id))
         (buffer (get-buffer-create (format "BBJ: %s" (bbj-descend response 'data 'title)))))
    (with-current-buffer buffer
      (erase-buffer)
      (bbj-mode)
      (setq wow response)
      (setq bbj-buffer-type 'thread
            bbj-*usermap* (alist-get 'usermap response)
            mode-line-process '(":~%e" bbj-user)
            header-line-format
            (format "~%s: %s"
             (alist-get 'user_name (alist-get (car (read-from-string
                 (bbj-descend response 'data 'author)))
               bbj-*usermap*))
             (bbj-descend response 'data 'title)))
      (setq-local thread-id id)
      (bbj-insert-sep t)
      (loop for message across (bbj-descend response 'data 'messages) do
            (bbj-render-post message))
      (bbj-postprocess))
    (switch-to-buffer buffer)
    (setq buffer-read-only t)))
