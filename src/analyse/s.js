const base = "/api";
const users = base + "/users";
let endpoint = users + "/list";

var name = "Michael";
const greeting = "Hello " + name;

const url = `${base}/users/${name}`;

fetch(url);

const data = fetch(base + "/data");
const nested = "/api/" + users + "/test";

function getUser(id) {
    const path = `${base}/users/${id}`;
    return fetch(path);
}