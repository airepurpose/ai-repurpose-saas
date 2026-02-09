const API = "http://127.0.0.1:8000";

// LOGIN
async function login() {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    const res = await fetch(API + "/login", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (res.ok) {
        localStorage.setItem("token", data.access_token);
        alert("Login successful");
    } else {
        alert(data.detail);
    }
}

// REPURPOSE
async function repurpose() {
    const token = localStorage.getItem("token");
    if (!token) {
        alert("Please login first");
        return;
    }

    const text = document.getElementById("text").value;

    const res = await fetch(API + "/repurpose", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
        },
        body: JSON.stringify({
            text: text,
            targets: ["twitter", "linkedin"]
        })
    });

    const data = await res.json();

    document.getElementById("output").textContent =
        JSON.stringify(data, null, 2);
}
