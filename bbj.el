(require 'json)
(require 'cl)

(defvar bbj-host "localhost")
(defvar bbj-port "7066")
(defvar bbj-width 80)

;; blah blah user servicable parts blah blaheiu hre  ;;;;;;;;;;r;r;r;r;;;q;q;;;
(defvar bbj-old-p (eq emacs-major-version 24))
(defvar bbj-logged-in nil)
(defvar bbj-user nil)
(defvar bbj-hash nil)
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

  (local-set-key (kbd "RET")     'bbj-enter)
  (local-set-key (kbd "l")       'bbj-enter)
  (local-set-key (kbd "o")       'bbj-enter)
  (local-set-key (kbd "<right>") 'bbj-enter)

  (local-set-key (kbd "q")       'quit-window)
  (local-set-key (kbd "<left>")  'quit-window)

  (local-set-key (kbd "+")       'bbj-compose)
  (local-set-key (kbd "c")       'bbj-compose)

  (local-set-key (kbd "C-c C-c") 'bbj-aux)
  (local-set-key (kbd "r")       'bbj-quote-current-post))

(ignore-errors
  (evil-set-initial-state 'bbj-mode 'emacs))

;;;; shit to put up with outdated emacs on the tilde ;;;;

(when (eq emacs-major-version 24)

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

;;;; network shit ;;;;

(defun bbj-descend (alist &rest keys)
  "Recursively retrieve symbols from a nested alist. A required beverage
for all JSON tourists."
  (while keys
    (setq alist (alist-get (pop keys) alist)))
  alist)


(defun bbj-request (method &rest pairs)
  "Poke netcat to poke the server who will hopefully poke us back"
  ;; json-false/json-nil are bound as nil here to stop them from being silly keywords
  (let (json message json-false json-null
        (data (list
          (cons 'user bbj-user)
          (cons 'auth_hash bbj-hash)
          (cons 'method method))))
    ;; populate a query with our hash and username, then the func arguments
    (while pairs
      (push (cons (pop pairs) (pop pairs)) data))

    (with-temp-buffer
      (insert (json-encode data))
      (call-process-region
       (point-min) (point-max)
       shell-file-name t t nil ;; meow meow
       "-c" (format "nc %s %s" bbj-host bbj-port))
      (setq json (progn (goto-char (point-min)) (json-read))))

    (if (eq json t) t ;; a few enpoints just return true/false
      (setq message (bbj-descend json 'error 'description))
      (case (bbj-descend json 'error 'code)
        ;; haha epic handling
        (4 (user-error
            (if bbj-logged-in message
              "Not logged in. Call M-x bbj-login")))
        ((5 6 7) (user-error message))
        (otherwise json)))))


(defun bbj-sethash (&optional password)
  "Either prompt for or take the arg `PASSWORD', and then sha256-hash it.
Sets it globally and also returns it."
  (interactive)
  (unless password (setq password
    (read-from-minibuffer "(Password)> ")))
  (setq bbj-hash (secure-hash 'sha256 password)))


(defun bbj-login ()
  "Prompts the user for a name and password. If it isn't registered, we'll take
care of that. Jumps to the index afterward. This function only needs to be used
once per emacs session."
  (interactive)
  (setq bbj-user (read-from-minibuffer "(BBJ Username)> "))
  (cond
   ((bbj-request "is_registered" 'target_user bbj-user)
    (bbj-sethash)
    (if (bbj-request "check_auth")
        (progn
          (setq bbj-logged-in t)
          (bbj-browse-index)
          (message "Logged in as %s!" bbj-user))
      (message "(Invalid Password!)")
      (run-at-time 1 nil #'bbj-login)))
   ((y-or-n-p (format "Register for BBJ as %s? " bbj-user))
    (bbj-sethash)
    (let ((response
           (bbj-request "user_register"
            ;; need to add some cute prompts for these
            'quip "" 'bio "")))
      (if (alist-get 'error response)
          (message "%s" (alist-get 'error response))
        (setq bbj-logged-in t)
        (bbj-browse-index)
        (message "Logged in as %s!" bbj-user))))))


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
  ;; does interactive work like this? i never checked tbh
  (interactive (push-mark))
  (goto-char (+ 1 bbj-width (point-min))))


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
                 (request (bbj-request "thread_create"
                   'body message
                   'title ,(read-from-minibuffer "(Thread Title)> ")
                   'tags ,(read-from-minibuffer "(Comma-seperated tags, if any)> "))))
            (if (numberp (bbj-descend request 'error 'code))
                (message "%s" request)
              (message "thread submitted")
              (bbj-browse-index))))))
     (thread
      `("Replying to thread (C-c C-c to send)"
        (lambda ()
          (let* ((message (bbj-consume-window (current-buffer)))
                 (request (bbj-request "thread_reply"
                            'body message 'thread_id ,thread-id)))
            (if (numberp (bbj-descend request 'error 'code))
                (message "%s" request)
              (message "reply submitted")
              (bbj-enter-thread ,thread-id)
              (goto-char (point-max))
              (bbj-point-to-post 'prev)
              (recenter nil)))))))))

    (apply #'bbj-compose-in-window params)))


(defun bbj-compose-in-window (title callback &rest cbargs)
  "Create a new buffer, pop it, set TITLE as the header line, and
assign CALLBACK to C-c C-c."
  (let ((buffer (get-buffer-create "*BBJ: Compose*")))
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
  (interactive)
  (with-current-buffer buffer
    (let ((content (buffer-substring-no-properties
                    (point-min) (point-max))))
      (quit-window t)
      content)))


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


(defun bbj-render-post (object)
  "Render an API object into the current buffer. Can be either the parent object
or any of its children."
  (let* ((userdata (cdr (assoc-string (alist-get 'author object) bbj-*usermap*)))
         (title (alist-get 'title object))
         (indicator (format ">>%s " (or title (alist-get 'post_id object)))))
    (insert (propertize indicator
      'face 'font-lock-function-name-face
      'type 'head 'data object))
    (when title (insert "\n"))
    (insert (propertize
      (concat "~" (alist-get 'name userdata) " ")
      'face 'font-lock-keyword-face))
    (insert (if (eq bbj-buffer-type 'index)
        (propertize (format "@ %s\n%s replies; last active %s\n"
            (bbj-timestring (alist-get 'created object))
            (alist-get 'reply_count object)
            (bbj-timestring (alist-get 'lastmod object)))
          'face 'font-lock-comment-face)
      (propertize (format "@ %s\n\n" (bbj-timestring (alist-get 'created object)))
        'face 'font-lock-comment-face)))
    (when (eq bbj-buffer-type 'thread)
        (bbj-render-body (alist-get 'body object)))
    (bbj-insert-sep)))


;; (defun bbj-render-tag-span (dom)
;;   "A slightly modified version of `shr-tag-span' which handles quotes and stuff."
;;   (let ((class (if bbj-old-p
;;                    (assq :class (cdr dom))
;;                    (dom-attr dom 'class))))
;;     (dolist (sub (if (consp (car dom)) (cddr (car dom)) (cddr dom)))
;;       (if (stringp sub)
;;           (cond
;;            ((equal class "quote")
;;             (insert (propertize sub
;;               'face 'font-lock-constant-face
;;               'type 'quote)))
;;            ((equal class "linequote")
;;             (insert (propertize sub
;;               'face 'font-lock-string-face
;;               'type 'linequote)))
;;            (t (shr-insert sub)))
;;         (shr-descend sub)))))

(defun bbj-render-tag-span (dom)
  "A highly bastardized version of `shr-tag-span', beaten and maimed until
it worked on emacs 24."
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
     (text (shr-insert text)))))


(defun bbj-mksep ()
  (format "\n%s\n" (make-string bbj-width ?\-)))


(defun bbj-insert-sep (&optional drop-newline)
  (let ((sep (bbj-mksep)))
    (insert (propertize
      (if drop-newline (subseq sep 1) sep)
      'face 'font-lock-comment-face
      'type 'end))))


(defun bbj-browse-index ()
  (interactive)
  (let* ((inhibit-read-only t)
         (buffer (get-buffer-create "*BBJ Index*"))
         (response (bbj-request "thread_index"))
         (bbj-*usermap* (alist-get 'usermap response)))
    (with-current-buffer buffer
      (erase-buffer)
      (bbj-mode)
      (setq bbj-buffer-type 'index
            bbj-*usermap* (alist-get 'usermap response))
      (bbj-insert-sep t)
      (loop for thread across (alist-get 'threads response) do
            (bbj-render-post thread))
      (bbj-postprocess))
    (switch-to-buffer buffer)
    (setq buffer-read-only t)))


(defun bbj-enter-thread (id)
  (interactive)
  (let* ((inhibit-read-only t)
         (response (bbj-request "thread_load" 'thread_id id))
         (buffer (get-buffer-create (format "BBJ: %s" (alist-get 'title response)))))
    (with-current-buffer buffer
      (erase-buffer)
      (bbj-mode)
      (setq bbj-buffer-type 'thread
            bbj-*usermap* (alist-get 'usermap response))
      (setq-local thread-id id)
      (bbj-insert-sep t)
      (bbj-render-post response)
      (loop for reply across (alist-get 'replies response) do
            (bbj-render-post reply))
      (bbj-postprocess))
    (switch-to-buffer buffer)
    (setq buffer-read-only t)))
