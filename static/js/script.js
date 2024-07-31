async function sendRequest() {
    const response = await fetch('/api/hello');
    const data = await response.json();
    alert(data.message);
}
