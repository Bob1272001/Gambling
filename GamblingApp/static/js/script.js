document.addEventListener("DOMContentLoaded", function () {
    const betsTableBody = document.querySelector("#betsTable tbody");
    const usersSelect = document.getElementById("usersSelect");
    const currencyDisplay = document.getElementById("currencyDisplay");
    const betForm = document.getElementById("betForm");
    const teamSelect = document.getElementById("teamSelect");
    const oddsDisplay = document.getElementById("oddsDisplay");
    const upcomingMatchesTableBody = document.querySelector("#upcomingMatchesTable tbody");

    if (!betsTableBody || !usersSelect || !currencyDisplay || !betForm || !upcomingMatchesTableBody) {
        console.error("One or more required DOM elements not found. Please verify the HTML structure.");
        return;
    }

    //load all users into the dropdown
    function loadUsers() {
        fetch("/api/get_users")
            .then(response => response.json())
            .then(data => {
                usersSelect.innerHTML = ""; 
                data.users.forEach(user => {
                    const option = document.createElement("option");
                    option.value = user[0]; 
                    option.textContent = user[0];
                    usersSelect.appendChild(option);
                });

                if (usersSelect.value) {
                    loadUserCurrency(usersSelect.value);
                    loadUserBets(usersSelect.value);
                }
            })
            .catch(error => console.error("Error loading users:", error));
    }

    //load currency for a selected user
    function loadUserCurrency(username) {
        fetch(`/api/get_user_currency?username=${username}`)
            .then(response => response.json())
            .then(data => {
                currencyDisplay.textContent = `Currency: ${data.currency}`;
            })
            .catch(error => console.error("Error loading user currency:", error));
    }

    //load bets for the selected user
    function loadUserBets(username) {
        fetch(`/api/get_user_bets?username=${username}`)
            .then(response => response.json())
            .then(data => {
                betsTableBody.innerHTML = ""; 

                if (!data.bets || !Array.isArray(data.bets)) {
                    console.error("Invalid data format for bets.");
                    return;
                }

                data.bets.forEach(bet => {
                    const tr = document.createElement("tr");

                    bet.forEach(cell => {
                        const td = document.createElement("td");
                        td.textContent = cell;
                        tr.appendChild(td);
                    });

                    const endBetTd = document.createElement("td");
                    const endBetButton = document.createElement("button");
                    endBetButton.textContent = "End Bet";
                    endBetButton.addEventListener("click", async function () {
                        await endBet(username, bet[0]); 
                        loadUserBets(username); 
                        loadUserCurrency(username); 
                    });

                    endBetTd.appendChild(endBetButton);
                    tr.appendChild(endBetTd);

                    betsTableBody.appendChild(tr);
                });
            })
            .catch(error => console.error("Error loading user bets:", error));
    }

    //load upcoming matches
    function loadUpcomingMatches() {
        fetch("/api/upcoming_matches")
            .then(response => response.json())
            .then(data => {
                upcomingMatchesTableBody.innerHTML = ""; 

                if (!data.matches || !Array.isArray(data.matches)) {
                    console.error("Invalid data format for matches.");
                    return;
                }

                data.matches.forEach(match => {
                    const tr = document.createElement("tr");

                    match.forEach((cell, index) => {
                        const td = document.createElement("td");
                        
                        if (index === 3 && typeof cell === 'string' && cell.includes(',')) {
                            const oddsArray = cell.split(",");
                            td.textContent = `Red: ${oddsArray[0]}, Blue: ${oddsArray[1]}`;
                        } else {
                            td.textContent = cell;
                        }
                        tr.appendChild(td);
                    });

                    const actionTd = document.createElement("td");
                    const placeBetButton = document.createElement("button");
                    placeBetButton.textContent = "Place Bet";
                    placeBetButton.addEventListener("click", function () {
                        document.getElementById("matchId").value = match[0];

                        if (typeof match[3] === 'string' && match[3].includes(',')) {
                            const oddsArray = match[3].split(",");
                            oddsDisplay.textContent = `Red Team Odds: ${oddsArray[0]}, Blue Team Odds: ${oddsArray[1]}`;
                        } else {
                            oddsDisplay.textContent = "Odds unavailable";
                        }
                    });

                    actionTd.appendChild(placeBetButton);
                    tr.appendChild(actionTd);

                    upcomingMatchesTableBody.appendChild(tr);
                });
            })
            .catch(error => console.error("Error loading upcoming matches:", error));
    }

    // user selection change
    usersSelect.addEventListener("change", function () {
        const selectedUsername = usersSelect.value;
        loadUserCurrency(selectedUsername);
        loadUserBets(selectedUsername);
    });

    // betting form submission
    betForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        const formData = new FormData(betForm);
        const data = Object.fromEntries(formData.entries());

        data.Username = usersSelect.value;
        data.Amount = parseInt(data.Amount);
        data.Team = teamSelect.value;

        try {
            const response = await fetch('/api/place_bet', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            alert(result.message || "Bet placed successfully!");
            loadUserBets(usersSelect.value);
            loadUserCurrency(usersSelect.value);
        } catch (error) {
            console.error("Error placing bet:", error);
        }
    });

    loadUsers();
    loadUpcomingMatches();
    setInterval(loadUpcomingMatches, 30000); 
});
