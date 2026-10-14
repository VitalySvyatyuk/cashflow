/** Заморозка ведущим: экран приглушён, кнопки недоступны. */
export function PauseOverlay() {
  return (
    <div className="pause-overlay">
      <div className="pause-banner">Игра на паузе</div>
    </div>
  );
}
