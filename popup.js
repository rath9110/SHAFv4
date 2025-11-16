document.addEventListener("DOMContentLoaded", async () => {
    console.log("Popup loaded!");
    
    const detectedProduct = document.getElementById("detectedProduct");
    const copyButton = document.getElementById("copyProductName");
    const searchResults = document.getElementById("searchResults");
    const traderaContainer = document.querySelector("#traderaResults .listings-container");
    const blocketContainer = document.querySelector("#blocketResults .listings-container");

    const seeMoreTradera = document.getElementById("seeMoreTradera");
    const seeMoreBlocket = document.getElementById("seeMoreBlocket");

    seeMoreTradera.style.display = "inline-block";
    seeMoreBlocket.style.display = "inline-block";

    const tab = await getCurrentTab();
    const pageKey = `page_${tab.url}`;

    chrome.storage.local.get(["currentPage", pageKey], (data) => {
        const currentPage = data.currentPage;

        if (currentPage !== pageKey) {
            console.log(`[Popup] Page changed. Clearing old results.`);
            chrome.storage.local.set({ "currentPage": pageKey });
            chrome.storage.local.remove([currentPage]);
        }

        const pageData = data[pageKey] || {};
        if (pageData.lastDetectedProduct) {
            detectedProduct.innerText = `Searching for: ${pageData.lastDetectedProduct}`;
            copyButton.style.display = "inline-block";
            updateSeeMoreLinks(pageData.lastDetectedProduct);
        } else {
            detectedProduct.innerText = "No product detected yet...";
        }

        if (pageData.lastTraderaResults) {
            traderaContainer.innerHTML = pageData.lastTraderaResults;
        } else {
            traderaContainer.innerHTML = "";
        }

        if (pageData.lastBlocketResults) {
            blocketContainer.innerHTML = pageData.lastBlocketResults;
        } else {
            blocketContainer.innerHTML = ""; // Ensure old results are cleared
        }
    });

    injectContentScript();

    chrome.runtime.onMessage.addListener((message) => {
        console.log("Received message:", message);
        if (message.type === "product_detected") {
            let trimmedTitle = trimProductName(message.title);
            console.log(`Updating Popup: ${trimmedTitle}`);

            chrome.storage.local.get([pageKey], (data) => {
                let pageData = data[pageKey] || {};

                // Only fetch if the detected product is new or no results exist for this page
                if (!pageData.lastDetectedProduct || pageData.lastDetectedProduct !== trimmedTitle ||
                    !pageData.lastTraderaResults || !pageData.lastBlocketResults) {

                    console.log("[Popup] Detected new product or missing results. Fetching new data...");

                    pageData.lastDetectedProduct = trimmedTitle;
                    chrome.storage.local.set({ [pageKey]: pageData });

                    detectedProduct.innerText = `Searching for: ${trimmedTitle}`;
                    copyButton.style.display = "inline-block";
                    updateSeeMoreLinks(trimmedTitle);
                    searchResults.innerHTML = `<p>Fetching related listings...</p>`;
                    fetchRelatedProducts(trimmedTitle, pageKey);
                } else {
                    console.log("[Popup] Product already detected with stored results. No new request sent.");
                }
            });
        }
    });

    copyButton.addEventListener("click", () => {
        chrome.storage.local.get([pageKey], (data) => {
            let searchTerm = data[pageKey]?.lastDetectedProduct;
            if (!searchTerm) return;
            navigator.clipboard.writeText(searchTerm).then(() => {
                console.log(`Copied to clipboard: ${searchTerm}`);
            }).catch(err => {
                console.error("Failed to copy text:", err);
            });
        });
    });
});

function injectContentScript() {
    console.log("Injecting content script...");
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs.length === 0) {
            console.error("No active tab found.");
            return;
        }
        chrome.scripting.executeScript({
            target: { tabId: tabs[0].id },
            files: ["content.js"]
        }).then(() => {
            console.log("Content script injected successfully.");
        }).catch(err => {
            console.error("Error injecting content script:", err);
        });
    });
}

async function getCurrentTab() {
    return new Promise((resolve) => {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            resolve(tabs[0]);
        });
    });
}

function trimProductName(name) {
    return name.split(" ").slice(0, 4).join(" ");
}

async function fetchRelatedProducts(searchTerm, pageKey) {
    console.log(`[Popup] Sending request to fetching service for: "${searchTerm}"`);

    searchResults.innerHTML = `<p> Searching for "${searchTerm}"...</p>`;

    const seeMoreTradera = document.getElementById("seeMoreTradera");
    const seeMoreBlocket = document.getElementById("seeMoreBlocket");

    const encoded = encodeURIComponent(searchTerm);
    if (seeMoreTradera) {
        seeMoreTradera.href = `https://www.tradera.com/search?q=${encoded}`;
        console.log("[Popup] seeMoreTradera href set to:", seeMoreTradera.href);
    }
    if (seeMoreBlocket) {
        seeMoreBlocket.href = `https://www.blocket.se/annonser/hela_sverige?q=${encoded}`;
        console.log("[Popup] seeMoreBlocket href set to:", seeMoreBlocket.href);
    }

    try {
        const response = await fetch(`https://shafv4-production.up.railway.app/related-products?product_name=${encodeURIComponent(searchTerm)}`, {
            method: "GET",
            headers: { "Content-Type": "application/json" }
        });
        console.log('https://shafv4-production.up.railway.app/related-products?product_name=' + encodeURIComponent(searchTerm));
        console.log(response.body)

        console.log(`[Popup] Response received from fetching service. Status: ${response.status}`);

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        console.log(`[Popup] Data received:`, data);

        if (data.error) {
            console.error(`[Popup] Error in response: ${data.error}`);
            searchResults.innerHTML = `<p>Error: ${data.error}</p>`;
            return;
        }

        searchResults.innerHTML = "<p>Listings found:</p>";
        traderaContainer.innerHTML = "";
        blocketContainer.innerHTML = "";

        function createListing(item) {
            const listingDiv = document.createElement("div");
            listingDiv.className = "listing";

            const title = document.createElement("span");
            title.className = "listing-title";
            title.textContent = item.title;

            const image = document.createElement("img");
            image.src = item.image;
            image.alt = item.title;
            image.className = "listing-image";

            const price = document.createElement("p");
            price.textContent = `${item.price}`;

            const link = document.createElement("a");
            link.href = item.link;
            link.target = "_blank";
            link.appendChild(image);
            link.appendChild(title);
            listingDiv.appendChild(link);
            listingDiv.appendChild(price);

            return listingDiv;
        }

        let traderaHTML = "";
        let blocketHTML = "";

        if (data.tradera && data.tradera.length > 0) {
            console.log(`[Popup] Updating Tradera listings.`);
            data.tradera.forEach(item => {
                let listing = createListing(item);
                traderaContainer.appendChild(listing);
                traderaHTML += listing.outerHTML;
            });
        } else {
            console.log(`[Popup] No listings found on Tradera.`);
            traderaContainer.innerHTML = "<p>No listings found on Tradera.</p>";
            traderaHTML = "<p>No listings found on Tradera.</p>";
        }

        if (data.blocket && data.blocket.length > 0) {
            console.log(`[Popup] Updating Blocket listings.`);
            data.blocket.forEach(item => {
                let listing = createListing(item);
                blocketContainer.appendChild(listing);
                blocketHTML += listing.outerHTML;
            });
        } else {
            console.log(`[Popup] No listings found on Blocket.`);
            blocketContainer.innerHTML = "<p>No listings found on Blocket.</p>";
            blocketHTML = "<p>No listings found on Blocket.</p>";
        }

        chrome.storage.local.set({
            [pageKey]: {
                lastDetectedProduct: searchTerm,
                lastTraderaResults: traderaHTML,
                lastBlocketResults: blocketHTML
            }
        });

        console.log(`[Popup] Listings stored successfully.`);

    } catch (error) {
        console.error(`[Popup] Network error while fetching listings: ${error.message}`);
        searchResults.innerHTML = `<p>Error fetching listings: ${error.message}</p>`;
    }
}

function updateSeeMoreLinks(searchTerm) {
    const seeMoreTradera = document.getElementById("seeMoreTradera");
    const seeMoreBlocket = document.getElementById("seeMoreBlocket");

    if (!seeMoreTradera || !seeMoreBlocket) {
        console.warn("[Popup] See-more links not found in DOM");
        return;
    }

    const encoded = encodeURIComponent(searchTerm);

    // IMPORTANT: full absolute URLs with https://
    seeMoreTradera.href = `https://www.tradera.com/search?q=${encoded}`;
    seeMoreBlocket.href = `https://www.blocket.se/annonser/hela_sverige?q=${encoded}`;

    console.log("[Popup] Updated see-more links:", {
        tradera: seeMoreTradera.href,
        blocket: seeMoreBlocket.href,
    });
}
