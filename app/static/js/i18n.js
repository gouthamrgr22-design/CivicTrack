
/*
 * CIVICTRACK INTERNATIONALIZATION ENGINE
 * Supports Indian language packs.
 */

const CivicI18n = (() => {

    const STORAGE_KEY = "civictrack_language";

    const languages = {
        en: "English",
        as: "অসমীয়া",
        bn: "বাংলা",
        brx: "बड़ो",
        doi: "डोगरी",
        gu: "ગુજરાતી",
        hi: "हिन्दी",
        kn: "ಕನ್ನಡ",
        ks: "कॉशुर",
        kok: "कोंकणी",
        mai: "मैथिली",
        ml: "മലയാളം",
        mni: "মৈতৈলোন্",
        mr: "मराठी",
        ne: "नेपाली",
        or: "ଓଡ଼ିଆ",
        pa: "ਪੰਜਾਬੀ",
        sa: "संस्कृतम्",
        sat: "ᱥᱟᱱᱛᱟᱲᱤ",
        sd: "سنڌي",
        ta: "தமிழ்",
        te: "తెలుగు",
        ur: "اردو"
    };

    let currentLanguage = "en";
    let translations = {};

    async function setLanguage(language) {

        if (!languages[language]) {
            console.error("Unsupported language:", language);
            return;
        }

        try {

            const response = await fetch(
                `/static/js/translations/${language}.json`,
                { cache: "no-cache" }
            );

            if (!response.ok) {
                throw new Error("Translation file unavailable.");
            }

            translations = await response.json();

            currentLanguage = language;

            localStorage.setItem(STORAGE_KEY, language);

            document.documentElement.lang = language;

            document.documentElement.dir =
                language === "ur" ? "rtl" : "ltr";

            translatePage();

            document.dispatchEvent(
                new CustomEvent("civictrack:languageChanged", {
                    detail: { language }
                })
            );

        } catch (error) {

            console.error("Language loading failed:", error);

        }
    }

    function translate(key) {

        return key.split(".").reduce(
            (value, part) => value?.[part],
            translations
        ) ?? key;

    }

    function translatePage() {

        document.querySelectorAll("[data-i18n]").forEach(element => {

            const key = element.dataset.i18n;

            element.textContent = translate(key);

        });

        document.querySelectorAll("[data-i18n-placeholder]")
            .forEach(element => {

                element.placeholder = translate(
                    element.dataset.i18nPlaceholder
                );

            });

        document.querySelectorAll("[data-i18n-aria]")
            .forEach(element => {

                element.setAttribute(
                    "aria-label",
                    translate(element.dataset.i18nAria)
                );

            });

    }

    async function initialize() {

        const savedLanguage =
            localStorage.getItem(STORAGE_KEY) || "en";

        await setLanguage(savedLanguage);

        const selector = document.querySelector("#language-selector");

        if (selector) {

            selector.value = currentLanguage;

            selector.addEventListener("change", event => {
                setLanguage(event.target.value);
            });

        }

    }

    return {
        languages,
        initialize,
        setLanguage,
        translate,
        translatePage,
        getLanguage: () => currentLanguage
    };

})();

document.addEventListener("DOMContentLoaded", () => {
    CivicI18n.initialize();
});

