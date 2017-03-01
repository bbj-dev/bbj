(require 'json)

(defvar bbj:host "localhost")
(defvar bbj:port "7066")
(defvar bbj:logged-in nil)
(defvar bbj:user nil)
(defvar bbj:hash nil)

(make-variable-buffer-local
 (defvar bbj:aux-callback #'ignore))

(define-derived-mode bbj-mode fundamental-mode "[BBJ]"
  "Mode for browsing and posting to BBJ."
  :group 'bbj-mode
  (local-set-key (kbd "C-c C-c") 'bbj:aux)
  (local-set-key (kbd "+") 'bbj:compose)
  (local-set-key (kbd "RET") 'bbj:enter))

(defun bbj:request (&rest cells)
  (push (cons 'user bbj:user) cells)
  (push (cons 'auth_hash bbj:hash) cells)
  (with-temp-buffer
    (insert (json-encode cells))
    (shell-command-on-region
     (point-min) (point-max)
     (format "nc %s %s" bbj:host bbj:port)))
  (with-current-buffer "*Shell Command Output*"
    (goto-char (point-min))
    (let (json-false json-null)
      (json-read))))


(defun bbj:sethash (&optional password)
  (unless password (setq password
    (read-from-minibuffer "(Password)> ")))
  (setq bbj:hash (secure-hash 'sha256 password)))


(defun bbj:login ()
  (interactive)
  (setq bbj:user (read-from-minibuffer "(BBJ Username)> "))
  (cond
   ((bbj:request '(method . "is_registered")
                 `(target_user . ,bbj:user))
    (bbj:sethash)
    (unless (bbj:request '(method . "check_auth"))
      (message "(Invalid Password!)")))
   ((y-or-n-p (format "Register for BBJ as %s? " bbj:user))
    (let ((response (bbj:request
                     (cons 'method "user_register")
                     (cons 'auth_hash (bbj:sethash))
                     (cons 'user bbj:user)
                     (cons 'quip (read-from-minibuffer "(Quip)> "))
                     (cons 'bio (read-from-minibuffer "(Bio)> ")))))
      (if (alist-get 'error response)
          (message "%s" (alist-get 'error response))
        (setq bbj:logged-in t)
        (message "Logged in as %s!" bbj:user))))))


(defun bbj:compose-in-window (title callback &rest cbargs)
  (let ((buffer (get-buffer-create "*BBJ: Compose*")))
    (pop-to-buffer buffer)
    (with-current-buffer buffer
      (erase-buffer)
      (bbj-mode)
      (setq header-line-format title
            bbj:aux-callback callback))))


(defun bbj:consume-window (buffer)
  (interactive)
  (with-current-buffer buffer
    (let ((content (buffer-substring-no-properties
                    (point-min) (point-max))))
      (quit-window t)
      content)))


(defun bbj:browse-index ()
  (interactive)
  (let ((response (bbj:request '(method . "thread_index"))))
    (cl-loop for thread across (alist-get 'threads response) do
             (message "%s" thread))))
