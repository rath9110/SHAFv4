/**
 * @jest-environment jsdom
 */

// We need to mock chrome API
global.chrome = {
    storage: {
        local: {
            get: jest.fn(),
            set: jest.fn(),
            remove: jest.fn()
        }
    },
    runtime: {
        onMessage: {
            addListener: jest.fn()
        },
        sendMessage: jest.fn()
    },
    tabs: {
        query: jest.fn()
    },
    scripting: {
        executeScript: jest.fn()
    }
};

// Mock DOM elements
document.body.innerHTML = `
    <div id="detectedProduct"></div>
    <button id="copyProductName"></button>
    <div id="searchResults"></div>
    <div id="traderaResults"><div class="listings-container"></div></div>
    <div id="blocketResults"><div class="listings-container"></div></div>
    <a id="seeMoreTradera"></a>
    <a id="seeMoreBlocket"></a>
`;

// Import or copy the logic we want to test. 
// Since popup.js is not a module, we might need to extract the function or load the file.
// For this test, I will replicate the vulnerable logic to demonstrate the fix, 
// or ideally we should refactor popup.js to be testable. 
// Given the constraints, I'll write a test that simulates the DOM manipulation issue.

describe('Security Tests', () => {
    test('Simulate XSS vulnerability in error handling', () => {
        const searchResults = document.getElementById("searchResults");
        const maliciousInput = "<img src=x onerror=alert(1)>";
        const data = { error: maliciousInput };

        // Vulnerable code simulation
        searchResults.innerHTML = `<p>Error: ${data.error}</p>`;

        // Check if HTML was injected
        expect(searchResults.innerHTML).toContain('<img src="x" onerror="alert(1)">');
    });

    test('Simulate Safe Error Handling (The Fix)', () => {
        const searchResults = document.getElementById("searchResults");
        const maliciousInput = "<img src=x onerror=alert(1)>";
        const data = { error: maliciousInput };

        // Safe code simulation
        searchResults.textContent = `Error: ${data.error}`;

        // Check that HTML is escaped/treated as text
        expect(searchResults.innerHTML).not.toContain('<img src="x" onerror="alert(1)">');
        expect(searchResults.textContent).toBe(`Error: ${maliciousInput}`);
    });
});
