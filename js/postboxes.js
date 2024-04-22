function revealPostReplyBox(post_id) {
    domElement = document.getElementById("replyBox" + post_id)
    document.getElementById("replyLink" + post_id).remove()

    form = document.createElement("form")
    form.setAttribute("method", "post")
    form.setAttribute("action", "/threadReply")

    textarea = document.createElement("textarea")
    textarea.setAttribute("class", "directReplyBox")
    textarea.setAttribute("id", "postContent")
    textarea.setAttribute("name", "postContent")
    textarea.setAttribute("rows", "10")
    textarea.setAttribute("cols", "50")
    textarea.value = ">>" + post_id + " \n"

    input = document.createElement("input")
    input.setAttribute("name", "threadId")
    input.value = thread_id
    input.style = "display:none"

    submit = document.createElement("input")
    submit.setAttribute("class", "directReplyBox")
    submit.setAttribute("type", "submit")
    submit.setAttribute("value", "Submit")

    form.appendChild(textarea)
    form.appendChild(input)
    form.appendChild(document.createElement("br"))
    form.appendChild(submit)

    domElement.appendChild(form)

}

function revealThreadCreateForm() {
    form = document.getElementById("threadCreateBox")
    if (form.style.display == "none") {
        form.style.display = "block"
    } else {
        form.style.display = "none"
    }
    
}