"use strict";
const isStatic = document.body.dataset.static === "1";

// Мобільне меню
const burger = document.querySelector(".burger");
const nav = document.getElementById("menu");
burger.addEventListener("click", () => {
  const open = nav.classList.toggle("open");
  burger.setAttribute("aria-expanded", open);
  document.body.classList.toggle("no-scroll", open);
});
nav.addEventListener("click", (e) => {
  if (e.target.closest("a") && nav.classList.contains("open")) burger.click();
});

// Модальне вікно підтвердження видалення
const modal = document.getElementById("confirm");
let pendingForm = null;
const closeModal = () => {
  modal.hidden = true;
  document.body.classList.remove("no-scroll");
  pendingForm = null;
};
document.querySelectorAll("form[data-confirm]").forEach((form) => {
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    pendingForm = form;
    document.getElementById("confirm-text").textContent = form.dataset.confirm;
    modal.hidden = false;
    document.body.classList.add("no-scroll");
    document.getElementById("confirm-ok").focus();
  });
});
document.getElementById("confirm-ok").addEventListener("click", () => {
  const form = pendingForm;
  closeModal();
  if (form) form.submit();
});
modal.addEventListener("click", (e) => {
  if (e.target === modal || e.target.hasAttribute("data-close")) closeModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !modal.hidden) closeModal();
});

// Фільтр лікарів за спеціальністю
document.querySelectorAll(".chip[data-filter]").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.querySelectorAll(".chip").forEach((c) => c.classList.toggle("active", c === chip));
    const f = chip.dataset.filter;
    document.querySelectorAll(".doc[data-spec]").forEach((card) => {
      card.hidden = f !== "all" && card.dataset.spec !== f;
    });
  });
});

// Форма запису: перевірка на клієнті
const form = document.getElementById("appt");
if (form) {
  const f = form.elements;
  const pre = new URLSearchParams(location.search).get("doctor");
  if (pre && !f.doctor_id.value) f.doctor_id.value = pre;

  form.addEventListener("submit", (e) => {
    const today = new Date().toISOString().slice(0, 10);
    const rules = {
      name: [f.name.value.trim().length >= 2, "Введіть ім'я (мінімум 2 літери)"],
      phone: [/^\+?[0-9 ()\-]{10,16}$/.test(f.phone.value.trim()), "Введіть телефон, наприклад +380501234567"],
      doctor_id: [f.doctor_id.value !== "", "Оберіть лікаря"],
      visit_date: [f.visit_date.value !== "" && f.visit_date.value >= today, "Оберіть дату не раніше сьогодні"],
    };
    let ok = true;
    for (const [key, [valid, msg]] of Object.entries(rules)) {
      f[key].parentNode.querySelector(".err").textContent = valid ? "" : msg;
      f[key].setAttribute("aria-invalid", !valid);
      if (!valid) ok = false;
    }
    if (!ok) { e.preventDefault(); return; }
    if (!isStatic) return; // далі перевіряє сервер

    // На GitHub Pages сервера немає: зберігаємо заявку в браузері
    e.preventDefault();
    const list = JSON.parse(localStorage.getItem("appointments") || "[]");
    list.push({ name: f.name.value, phone: f.phone.value, doctor_id: f.doctor_id.value,
                visit_date: f.visit_date.value, comment: f.comment.value });
    localStorage.setItem("appointments", JSON.stringify(list));
    form.reset();
    document.getElementById("done").hidden = false;
  });
}
