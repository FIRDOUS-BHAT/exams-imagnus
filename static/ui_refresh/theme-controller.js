(function (window, document) {
  "use strict";

  var STORAGE_KEY = "imagnus-theme";
  var LEGACY_STORAGE_KEY = "gmtNightMode";
  var mediaQuery = window.matchMedia
    ? window.matchMedia("(prefers-color-scheme: dark)")
    : null;

  function canUseStorage() {
    try {
      return "localStorage" in window && window.localStorage !== null;
    } catch (error) {
      return false;
    }
  }

  function getStoredTheme() {
    if (!canUseStorage()) {
      return null;
    }

    try {
      var value = window.localStorage.getItem(STORAGE_KEY);
      if (value === "light" || value === "dark") {
        return value;
      }

      return window.localStorage.getItem(LEGACY_STORAGE_KEY) ? "dark" : null;
    } catch (error) {
      return null;
    }
  }

  function setStoredTheme(theme) {
    if (!canUseStorage()) {
      return;
    }

    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
      if (theme === "dark") {
        window.localStorage.setItem(LEGACY_STORAGE_KEY, "true");
      } else {
        window.localStorage.removeItem(LEGACY_STORAGE_KEY);
      }
    } catch (error) {
      return;
    }
  }

  function getSystemTheme() {
    return mediaQuery && mediaQuery.matches ? "dark" : "light";
  }

  function resolveTheme() {
    return getStoredTheme() || getSystemTheme();
  }

  function updateToggles(theme) {
    var nextTheme = theme === "dark" ? "light" : "dark";
    var label = theme === "dark" ? "Dark theme" : "Light theme";
    var compactLabel = theme === "dark" ? "Dark" : "Light";
    var ariaLabel = "Switch to " + nextTheme + " theme";
    var toggles = document.querySelectorAll("[data-theme-toggle]");

    toggles.forEach(function (toggle) {
      toggle.setAttribute("aria-label", ariaLabel);
      toggle.setAttribute("title", ariaLabel);
      toggle.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
      toggle.dataset.themeCurrent = theme;

      var labelNode = toggle.querySelector("[data-theme-label]");
      if (labelNode) {
        labelNode.textContent =
          toggle.dataset.themeCompact === "true" ? compactLabel : label;
      }
    });
  }

  function applyTheme(theme, persist) {
    var nextTheme = theme === "dark" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", nextTheme);
    document.documentElement.style.colorScheme = nextTheme;
    document.documentElement.classList.toggle("night-mode", nextTheme === "dark");

    if (document.body) {
      document.body.classList.toggle("night-mode", nextTheme === "dark");
    }

    updateToggles(nextTheme);

    if (persist) {
      setStoredTheme(nextTheme);
    }

    if (typeof window.CustomEvent === "function") {
      document.dispatchEvent(
        new window.CustomEvent("imagnus:themechange", {
          detail: { theme: nextTheme }
        })
      );
    }

    return nextTheme;
  }

  function toggleTheme() {
    var currentTheme =
      document.documentElement.getAttribute("data-theme") || resolveTheme();
    var nextTheme = currentTheme === "dark" ? "light" : "dark";
    return applyTheme(nextTheme, true);
  }

  function bindToggles() {
    document.querySelectorAll("[data-theme-toggle]").forEach(function (toggle) {
      if (toggle.dataset.themeBound === "true") {
        return;
      }

      toggle.dataset.themeBound = "true";
      toggle.addEventListener("click", function (event) {
        event.preventDefault();
        toggleTheme();
      });
    });
  }

  function bindLegacyNightModeToggle() {
    var legacyToggle = document.querySelector("#night-mode");
    if (!legacyToggle || legacyToggle.dataset.themeBound === "true") {
      return;
    }

    legacyToggle.dataset.themeBound = "true";
    legacyToggle.addEventListener("click", function (event) {
      event.preventDefault();
      toggleTheme();
    });
  }

  function init() {
    applyTheme(resolveTheme(), false);
    bindToggles();
    bindLegacyNightModeToggle();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  if (mediaQuery) {
    var syncWithSystem = function (event) {
      if (!getStoredTheme()) {
        applyTheme(event.matches ? "dark" : "light", false);
      }
    };

    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener("change", syncWithSystem);
    } else if (mediaQuery.addListener) {
      mediaQuery.addListener(syncWithSystem);
    }
  }

  window.ImagnusTheme = {
    apply: applyTheme,
    get: function () {
      return document.documentElement.getAttribute("data-theme") || resolveTheme();
    },
    toggle: toggleTheme,
  };
})(window, document);
