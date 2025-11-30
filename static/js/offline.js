let db;
const request = indexedDB.open("MCQOfflineDB", 1);

request.onupgradeneeded = function(event) {
    db = event.target.result;
    if (!db.objectStoreNames.contains("responses")) {
        db.createObjectStore("responses", { keyPath: "id", autoIncrement: true });
    }
};

request.onsuccess = function(event) {
    db = event.target.result;
};


function saveOffline(data) {
    const tx = db.transaction("responses", "readwrite");
    const store = tx.objectStore("responses");
    store.add(data);
}


document.getElementById("mcqForm").addEventListener("submit", function(e) {
    e.preventDefault();

    const data = {
        question1: document.querySelector('input[name="q1"]:checked').value,
        question2: document.querySelector('input[name="q2"]:checked').value,
        timestamp: new Date().toISOString()
    };

    if (!navigator.onLine) {
        saveOffline(data);
        document.getElementById("status").innerHTML =
            "<span style='color:red'>Offline. Response saved locally.</span>";
    } else {
        uploadToServer(data);
    }
});


function uploadToServer(data) {
    fetch("/upload_mcq", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(result => {
        document.getElementById("status").innerHTML =
            "<span style='color:green'>Uploaded Successfully</span>";
    })
    .catch(err => console.error(err));
}


window.addEventListener("online", syncOfflineData);

function syncOfflineData() {
    const tx = db.transaction("responses", "readwrite");
    const store = tx.objectStore("responses");
    const getAll = store.getAll();

    getAll.onsuccess = function() {
        const items = getAll.result;

        items.forEach(item => {
            fetch("/upload_mcq", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(item)
            })
            .then(res => res.json())
            .then(() => {
                store.delete(item.id);
                document.getElementById("status").innerHTML =
                    "<span style='color:green'>Synced offline data</span>";
            });
        });
    };
}
