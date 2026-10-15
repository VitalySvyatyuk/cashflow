// Админка карточек: показываем только поля, нужные для выбранного типа.
document.addEventListener("DOMContentLoaded", () => {
  const kind = document.getElementById("id_kind");
  if (!kind) return;
  const fieldsByKind = JSON.parse(kind.dataset.kindFields);
  const all = [...new Set(Object.values(fieldsByKind).flat())];
  const update = () => {
    const visible = fieldsByKind[kind.value] || [];
    for (const name of all) {
      const row = document.querySelector(`.form-row.field-${name}, .field-${name}`);
      if (row) row.style.display = visible.includes(name) ? "" : "none";
    }
  };
  kind.addEventListener("change", update);
  update();
});
