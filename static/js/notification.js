async function loadNotifications(){

    const response = await fetch("/patient/notifications");
    const data = await response.json();

    let unread = 0;
    let html = "";

    data.notifications.forEach(n => {

        if(!n.is_read){
            unread++;
        }

        html += `
            <div class="notification-item"
                 onclick="markRead(${n.notification_id})">
                 ${n.message}
            </div>
        `;
    });

    document.getElementById("notificationList").innerHTML =
        html || "No notifications";

    document.getElementById("notificationCount").innerText = unread;
}

async function markRead(id){

    await fetch(`/patient/read-notification/${id}`, {
        method:"POST"
    });

    loadNotifications();
}

document.getElementById("notificationBtn")?.addEventListener("click", ()=>{

    const dropdown = document.getElementById("notificationDropdown");

    if(dropdown.style.display === "block"){
        dropdown.style.display = "none";
    }else{
        dropdown.style.display = "block";
    }
});

setInterval(loadNotifications, 3000);

loadNotifications();