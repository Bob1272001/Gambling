document.addEventListener("DOMContentLoaded", function () {
    const createUserForm = document.getElementById("createUserForm");

    if (!createUserForm) {
        console.error("Create user form not found");
        return;
    }

    // Handle user creation form submission
    createUserForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        const formData = new FormData(createUserForm);
        const data = Object.fromEntries(formData.entries());

        try {
            console.log("Creating user:", data);
            const response = await fetch('/api/create_user', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            alert(result.message || "User created successfully!");

            // Store username in session storage
            sessionStorage.setItem("username", data.Username);

            // Redirect to the main betting page
            window.location.href = "/";
        } catch (error) {
            console.error("Error creating user:", error);
        }
    });
});
