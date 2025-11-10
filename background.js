chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "SEARCH_SECOND_HAND") {
        console.log("Searching for second-hand alternatives:", message.query);
        chrome.storage.local.set({ lastSearch: message.query });
    }
});
