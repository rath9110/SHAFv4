console.log("Content script injected and running!");

let lastDetectedProduct = "";

function cleanProductTitle(title) {
    const stopWords = [
        "and", "or", "between", "with", "without", "the", "a", "an", "for", "to", "of", "in", "on", "by", "med", ",", ".", "Apple", "Samsung", "smartphone"
    ];

    return title
        .split(/\s+/)
        .filter(word => !stopWords.includes(word.toLowerCase()))
        .join(" ");
}

function detectProductPage() {
    console.log("Running product detection...");

    let productTitleSelectors = [
        "h1", ".product-title", "#productTitle", ".page-title",
        ".product-name", ".title-1", ".pdp-title", "h1 span",
        "[itemprop='name']", "[data-product-name]", "[data-test='product-title']",
        "[class*='title']", "[class*='heading']", "meta[property='og:title']"
    ];

    for (let selector of productTitleSelectors) {
        let element = document.querySelector(selector);
        if (element && element.innerText.trim().length > 0) {
            let rawTitle = element.innerText.trim();
            let productTitle = cleanProductTitle(rawTitle);


            // Ensure the detected product is not a test value or invalid
            if (productTitle.toLowerCase().includes("test product name")) {
                console.warn("Skipping test product name detection.");
                return;
            }

            if (productTitle !== lastDetectedProduct) {
                console.log(`New Product Title Detected: ${productTitle}`);

                lastDetectedProduct = productTitle;

                chrome.storage.local.set({ "lastDetectedProduct": productTitle }, () => {
                    chrome.runtime.sendMessage({ type: "product_detected", title: productTitle });
                });
            } else {
                console.log("Product title unchanged, skipping update.");
            }
            return;
        }
    }

    console.log("No product title found.");
}

// Restore last detected product if available, but ignore test product names
chrome.storage.local.get("lastDetectedProduct", (data) => {
    if (data.lastDetectedProduct && data.lastDetectedProduct.trim().length > 0) {
        if (!data.lastDetectedProduct.toLowerCase().includes("test product name")) {
            lastDetectedProduct = data.lastDetectedProduct;
            console.log(`Restored last detected product: ${lastDetectedProduct}`);
            chrome.runtime.sendMessage({ type: "product_detected", title: lastDetectedProduct });
        } else {
            console.warn("Skipping restoration of test product name.");
            chrome.storage.local.remove("lastDetectedProduct");
        }
    }
});

detectProductPage();

// Re-detect product when user switches back to this tab
document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
        console.log("Tab became visible, re-detecting product...");
        detectProductPage();

        // Force send message even if product hasn't changed
        // This ensures popup updates when switching back to the tab
        if (lastDetectedProduct) {
            console.log(`Sending product message on tab visibility: ${lastDetectedProduct}`);
            chrome.runtime.sendMessage({ type: "product_detected", title: lastDetectedProduct });
        }
    }
});

setInterval(() => {
    console.log("Checking for product name update...");
    detectProductPage();
}, 2000);

