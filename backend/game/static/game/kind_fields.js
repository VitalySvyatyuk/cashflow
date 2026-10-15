// Админка карточек и клеток: показываем только поля, нужные для выбранного типа.
// У списка типа есть data-kind-fields: {значение: [имена полей]}.
document.addEventListener("DOMContentLoaded", () => {
  const select = document.querySelector("select[data-kind-fields]");
  if (!select) return;
  const fieldsByKind = JSON.parse(select.dataset.kindFields);
  const all = [...new Set(Object.values(fieldsByKind).flat())];
  const update = () => {
    const visible = fieldsByKind[select.value] || [];
    for (const name of all) {
      const row = document.querySelector(`.form-row.field-${name}, .field-${name}`);
      if (row) row.style.display = visible.includes(name) ? "" : "none";
    }
  };
  select.addEventListener("change", update);
  update();
});
