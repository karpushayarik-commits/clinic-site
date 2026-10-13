// У статичній версії (GitHub Pages) немає сервера: заявки зберігаємо в localStorage браузера.
(function () {
  var form = document.getElementById("appt");
  if (!form) return;
  var isStatic = document.body.dataset.static === "1";
  form.addEventListener("submit", function (e) {
    if (!isStatic) return; // на Flask валідує сервер
    e.preventDefault();
    var f = form.elements, ok = true, today = new Date().toISOString().slice(0, 10);
    var rules = {
      name: [f.name.value.trim().length >= 2, "Введіть ім'я (мінімум 2 літери)"],
      phone: [/^\+?[0-9 ()\-]{10,16}$/.test(f.phone.value.trim()), "Введіть телефон, наприклад +380501234567"],
      doctor_id: [f.doctor_id.value !== "", "Оберіть лікаря"],
      visit_date: [f.visit_date.value >= today && f.visit_date.value !== "", "Оберіть дату не раніше сьогодні"]
    };
    Object.keys(rules).forEach(function (k) {
      var msg = f[k].parentNode.querySelector(".err");
      msg.textContent = rules[k][0] ? "" : rules[k][1];
      if (!rules[k][0]) ok = false;
    });
    if (!ok) return;
    var list = JSON.parse(localStorage.getItem("appointments") || "[]");
    list.push({ name: f.name.value, phone: f.phone.value, doctor_id: f.doctor_id.value,
                visit_date: f.visit_date.value, comment: f.comment.value });
    localStorage.setItem("appointments", JSON.stringify(list));
    form.reset();
    document.getElementById("done").hidden = false;
  });
})();
