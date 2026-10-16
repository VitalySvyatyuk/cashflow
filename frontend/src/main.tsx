import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { applyTheme, loadTheme } from "./lib/theme";
import "./styles.css";

// Тема — до первой отрисовки, чтобы не мигала тема по умолчанию.
applyTheme(loadTheme());

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
