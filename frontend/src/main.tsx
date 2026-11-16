import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { IdiomaProvider } from "./i18n/IdiomaProvider";
import "./index.css";

const raiz = document.getElementById("root");
if (!raiz) throw new Error("Falta el elemento #root en index.html");

createRoot(raiz).render(
  <StrictMode>
    <IdiomaProvider>
      <App />
    </IdiomaProvider>
  </StrictMode>,
);
