import { BrowserRouter, Route, Routes } from "react-router";

import { HostGamePage } from "./pages/HostGamePage";
import { HostHomePage } from "./pages/HostHomePage";
import { JoinPage } from "./pages/JoinPage";
import { PlayerPage } from "./pages/PlayerPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<JoinPage />} />
        <Route path="/play/:code" element={<PlayerPage />} />
        <Route path="/host" element={<HostHomePage />} />
        <Route path="/host/:code" element={<HostGamePage />} />
      </Routes>
    </BrowserRouter>
  );
}
