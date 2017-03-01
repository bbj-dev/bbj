(require 'json)

(defvar bbj:host "localhost")
(defvar bbj:port "7066")
(defvar bbj:logged-in nil)
(defvar bbj:user nil)
(defvar bbj:hash nil)


(defun bbj:request (&rest cells)
  (with-temp-buffer
    (insert (json-encode cells))
    (shell-command-on-region
     (point-min) (point-max)
     (format "nc %s %s" bbj:host bbj:port)))
  (with-current-buffer "*Shell Command Output*"
    (json-read-from-string
     (buffer-substring-no-properties
      (point-min) (point-max)))))


(bbj:request '(user . "desvox")
             '(auth_hash . "nrr")
             '(method . "check_auth"))

(defun bbj:login ()
  (interactive)
  (setq bbj:user (read-from-minibuffer "(BBJ Username)> "))
  (if (bbj:request '(method . "is_registered")
                   `(target_user . ,bbj:user))
      (setq bbj:hash (secure-hash 'sha256 (read-from-minibuffer "(BBJ Password)> ")))
    (when (y-or-n-p (format "Register for BBJ as %s? " bbj:user))
      (message
       (bbj:request (cons 'auth_hash bbj:hash)
                    (cons 'user bbj:user)
                    (cons 'avatar nil)
                    (cons 'bio (read-from-minibuffer "(Enter a short bio about youself!)> ")))))))
