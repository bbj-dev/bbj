function divmod(x, y) {
    return [Math.floor(x / y), x % y];
}

function timestring(timestamp) {
    time_milliseconds = timestamp * 1000
    date = new Date(time_milliseconds);
    return date.toLocaleDateString() + " " + date.toLocaleTimeString()
}

function readable_delta(timestamp) {
    current_time_seconds = Date.now() / 1000
    delta = current_time_seconds - timestamp
    mod = divmod(delta, 3600)
    hours = mod[0]
    remainder = mod[1]
    if (hours > 48) {
        return timestring(timestamp)
    }
    else if (hours > 1) {
        return hours + " hours ago"
    }
    else if (hours == 1) {
        return "about an hour ago"
    }
    mod = divmod(remainder, 60)
    minutes = mod[0]
    remainder = mod[1]
    if (minutes > 1) {
        return minutes + " minutes ago"
    }
    return "less than a minute ago"
}

timestamps = document.getElementsByClassName("datetime")
for (let i = 0; i < timestamps.length; i++) {
    delta = readable_delta(timestamps[i].textContent)
    timestamps[i].textContent = delta
  } 