console.log("Content script injected and running! [Version: Tab-Switch-Fix-v2]");

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
        // Elgiganten-specific selectors (prioritized)
        "h1[data-testid='product-title']",
        "h1.product-title",
        "[data-testid='product-name']",
        // Generic selectors
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
            return true; // Product found
        }
    }

    console.log("No product title found.");
    return false; // No product found
}

// Run initial detection with retries for dynamically loaded content
let retryCount = 0;
const maxRetries = 8; // Try for 4 seconds (8 x 500ms)

function attemptDetection() {
    const found = detectProductPage();

    if (!found && retryCount < maxRetries) {
        retryCount++;
        console.log(`[Content] Product not found, retrying (${retryCount}/${maxRetries})...`);
        setTimeout(attemptDetection, 500);
    } else if (found) {
        console.log("[Content] ✓ Product detected successfully!");
    } else {
        console.log("[Content] ✗ No product found after retries");
    }
}

attemptDetection();

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

// Listen for requests from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "request_product") {
        console.log("[Content] Popup requested current product");
        if (lastDetectedProduct) {
            console.log(`[Content] Sending current product: ${lastDetectedProduct}`);
            chrome.runtime.sendMessage({ type: "product_detected", title: lastDetectedProduct });
        } else {
            console.log("[Content] No product detected yet, running detection...");
            detectProductPage();
        }
        sendResponse({ received: true });
        return true;
    }
});

setInterval(() => {
    console.log("Checking for product name update...");
    detectProductPage();
}, 2000);

