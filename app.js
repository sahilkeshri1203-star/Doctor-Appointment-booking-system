// Browser-only version: localStorage plays the role of appointments.db.
const defaultDoctors = [
  { id: 1, name: "Anita Sharma", specialization: "Cardiologist", fee: 800 },
  { id: 2, name: "Rahul Mehta", specialization: "Dermatologist", fee: 600 },
  { id: 3, name: "Priya Nair", specialization: "General Physician", fee: 500 }
];
let doctors = JSON.parse(localStorage.getItem("medibookDoctors")) || defaultDoctors;
let appointments = JSON.parse(localStorage.getItem("medibookAppointments")) || [];
const $ = (selector) => document.querySelector(selector);

function save() {
  localStorage.setItem("medibookDoctors", JSON.stringify(doctors));
  localStorage.setItem("medibookAppointments", JSON.stringify(appointments));
}
function showToast(message) {
  const toast = $("#toast"); toast.textContent = message; toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2800);
}
function renderDoctors() {
  const search = $("#doctorSearch").value.toLowerCase();
  const shown = doctors.filter(d => `${d.name} ${d.specialization}`.toLowerCase().includes(search));
  $("#doctorList").innerHTML = shown.length ? shown.map(d => `
    <article class="doctor-card"><div class="avatar">${d.name.split(" ").map(n => n[0]).slice(0,2).join("")}</div>
      <h3>Dr. ${d.name}</h3><p>${d.specialization}</p><p class="fee">₹${Number(d.fee).toLocaleString("en-IN")} consultation</p></article>`).join("") : `<p class="empty">No doctor matches your search.</p>`;
  $("#bookingDoctor").innerHTML = `<option value="">Select a doctor</option>` + doctors.map(d => `<option value="${d.id}">Dr. ${d.name} — ${d.specialization}</option>`).join("");
}
function renderAppointments() {
  const list = $("#appointmentList");
  if (!appointments.length) { list.innerHTML = `<div class="empty">No appointments yet. Your confirmed bookings will appear here.</div>`; return; }
  list.innerHTML = [...appointments].sort((a,b) => new Date(a.time) - new Date(b.time)).map(a => {
    const date = new Date(a.time), day = date.toLocaleDateString("en-IN", { day:"2-digit" }), month = date.toLocaleDateString("en-IN", { month:"short" });
    const time = date.toLocaleString("en-IN", { dateStyle:"medium", timeStyle:"short" });
    return `<article class="appointment ${a.status === "CANCELLED" ? "cancelled" : ""}">
      <div class="appointment-date">${month.toUpperCase()}<b>${day}</b></div><div class="appointment-details"><h3>Dr. ${a.doctorName} <span>·</span> ${a.patientName}</h3><p>${a.specialization} · ${time} · ${a.phone}</p></div>
      <span class="status">${a.status}</span>${a.status === "BOOKED" ? `<button class="cancel" onclick="cancelAppointment(${a.id})">Cancel</button>` : ""}</article>`;
  }).join("");
}
function cancelAppointment(id) {
  const appointment = appointments.find(a => a.id === id); if (!appointment) return;
  appointment.status = "CANCELLED"; save(); renderAppointments(); showToast("Appointment cancelled.");
}
window.cancelAppointment = cancelAppointment;

$("#showDoctorForm").addEventListener("click", () => $("#doctorFormBox").classList.toggle("hidden"));
$("#doctorSearch").addEventListener("input", renderDoctors);
$("#doctorForm").addEventListener("submit", event => {
  event.preventDefault();
  doctors.push({ id: Date.now(), name: $("#doctorName").value.trim(), specialization: $("#specialization").value.trim(), fee: $("#fee").value });
  save(); event.target.reset(); $("#doctorFormBox").classList.add("hidden"); renderDoctors(); showToast("Doctor added successfully.");
});
$("#bookingForm").addEventListener("submit", event => {
  event.preventDefault(); const doctor = doctors.find(d => d.id === Number($("#bookingDoctor").value)); const time = $("#appointmentTime").value;
  if (new Date(time) <= new Date()) return showToast("Choose a future appointment time.");
  if (appointments.some(a => a.doctorId === doctor.id && a.time === time && a.status === "BOOKED")) return showToast("This doctor already has a booking at that time.");
  appointments.push({ id: Date.now(), doctorId: doctor.id, doctorName: doctor.name, specialization: doctor.specialization, patientName: $("#patientName").value.trim(), phone: $("#phone").value.trim(), email: $("#email").value.trim(), time, status:"BOOKED" });
  save(); event.target.reset(); renderAppointments(); showToast("Appointment confirmed!"); location.hash = "appointments";
});
$("#clearData").addEventListener("click", () => { if (confirm("Reset all saved doctors and appointments?")) { doctors = [...defaultDoctors]; appointments = []; save(); renderDoctors(); renderAppointments(); showToast("Demo data reset."); } });
renderDoctors(); renderAppointments();
