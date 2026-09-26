"""Doctor Appointment Booking System

Concepts demonstrated: classes/objects, constructors, encapsulation,
inheritance, abstraction, polymorphism, and composition.
Only Python's standard library is required.
"""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


DB_FILE = Path(__file__).with_name("appointments.db")


class Database:
    """Owns the SQLite connection and database operations."""

    def __init__(self, filename: Path = DB_FILE):
        self.connection = sqlite3.connect(filename)
        self.connection.row_factory = sqlite3.Row

    def setup(self) -> None:
        self.connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS doctors (
                doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                specialization TEXT NOT NULL,
                fee REAL NOT NULL CHECK (fee >= 0)
            );
            CREATE TABLE IF NOT EXISTS patients (
                patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL UNIQUE,
                email TEXT
            );
            CREATE TABLE IF NOT EXISTS appointments (
                appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id INTEGER NOT NULL,
                patient_id INTEGER NOT NULL,
                appointment_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'BOOKED'
                    CHECK (status IN ('BOOKED', 'CANCELLED')),
                UNIQUE (doctor_id, appointment_time),
                FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id),
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
            );
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()


@dataclass
class Person(ABC):
    """Abstract parent class: it cannot be instantiated directly."""

    name: str

    @abstractmethod
    def description(self) -> str:
        pass


@dataclass
class Doctor(Person):
    doctor_id: int
    specialization: str
    fee: float

    def description(self) -> str:  # Polymorphism: Doctor's implementation
        return f"Dr. {self.name} | {self.specialization} | Rs. {self.fee:.2f}"


@dataclass
class Patient(Person):
    patient_id: int
    phone: str
    email: str | None

    def description(self) -> str:  # Polymorphism: Patient's implementation
        return f"{self.name} | Phone: {self.phone}"


class Appointment:
    """Encapsulation: status is changed through methods, not free-form edits."""

    def __init__(self, appointment_id: int, doctor_name: str, patient_name: str,
                 appointment_time: str, status: str):
        self.appointment_id = appointment_id
        self.doctor_name = doctor_name
        self.patient_name = patient_name
        self.appointment_time = appointment_time
        self._status = status

    @property
    def status(self) -> str:
        return self._status

    def cancel(self) -> None:
        if self._status == "CANCELLED":
            raise ValueError("This appointment is already cancelled.")
        self._status = "CANCELLED"

    def __str__(self) -> str:
        return (f"#{self.appointment_id}: Dr. {self.doctor_name} with "
                f"{self.patient_name} on {self.appointment_time} [{self.status}]")


class AppointmentService:
    """Business layer; composed with a Database object."""

    def __init__(self, database: Database):
        self._db = database

    def add_doctor(self, name: str, specialization: str, fee: float) -> None:
        self._db.connection.execute(
            "INSERT INTO doctors (name, specialization, fee) VALUES (?, ?, ?)",
            (name.strip(), specialization.strip(), fee),
        )
        self._db.connection.commit()

    def doctors(self, keyword: str = "") -> list[Doctor]:
        rows = self._db.connection.execute(
            """SELECT * FROM doctors
               WHERE name LIKE ? OR specialization LIKE ?
               ORDER BY specialization, name""",
            (f"%{keyword.strip()}%", f"%{keyword.strip()}%"),
        ).fetchall()
        return [Doctor(row["name"], row["doctor_id"], row["specialization"], row["fee"])
                for row in rows]

    def _get_or_create_patient(self, name: str, phone: str, email: str) -> int:
        row = self._db.connection.execute(
            "SELECT patient_id FROM patients WHERE phone = ?", (phone.strip(),)
        ).fetchone()
        if row:
            return row["patient_id"]
        cursor = self._db.connection.execute(
            "INSERT INTO patients (name, phone, email) VALUES (?, ?, ?)",
            (name.strip(), phone.strip(), email.strip() or None),
        )
        return cursor.lastrowid

    def book(self, doctor_id: int, patient_name: str, phone: str, email: str,
             time_text: str) -> int:
        # Validate the expected format before inserting.
        appointment_time = datetime.strptime(time_text, "%Y-%m-%d %H:%M")
        if appointment_time <= datetime.now():
            raise ValueError("Appointment time must be in the future.")
        if not self._db.connection.execute(
            "SELECT 1 FROM doctors WHERE doctor_id = ?", (doctor_id,)
        ).fetchone():
            raise ValueError("Doctor ID does not exist.")
        patient_id = self._get_or_create_patient(patient_name, phone, email)
        try:
            cursor = self._db.connection.execute(
                """INSERT INTO appointments (doctor_id, patient_id, appointment_time)
                   VALUES (?, ?, ?)""",
                (doctor_id, patient_id, appointment_time.strftime("%Y-%m-%d %H:%M")),
            )
            self._db.connection.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError as error:
            self._db.connection.rollback()
            raise ValueError("That doctor already has an appointment at this time.") from error

    def appointments(self, phone: str = "") -> list[Appointment]:
        query = """
            SELECT a.appointment_id, d.name AS doctor_name, p.name AS patient_name,
                   a.appointment_time, a.status
            FROM appointments a
            JOIN doctors d ON d.doctor_id = a.doctor_id
            JOIN patients p ON p.patient_id = a.patient_id
        """
        parameters: tuple[str, ...] = ()
        if phone.strip():
            query += " WHERE p.phone = ?"
            parameters = (phone.strip(),)
        query += " ORDER BY a.appointment_time"
        rows = self._db.connection.execute(query, parameters).fetchall()
        return [Appointment(row["appointment_id"], row["doctor_name"], row["patient_name"],
                            row["appointment_time"], row["status"]) for row in rows]

    def cancel(self, appointment_id: int) -> None:
        appointment = self._db.connection.execute(
            "SELECT status FROM appointments WHERE appointment_id = ?", (appointment_id,)
        ).fetchone()
        if not appointment:
            raise ValueError("Appointment ID does not exist.")
        if appointment["status"] == "CANCELLED":
            raise ValueError("This appointment is already cancelled.")
        self._db.connection.execute(
            "UPDATE appointments SET status = 'CANCELLED' WHERE appointment_id = ?",
            (appointment_id,),
        )
        self._db.connection.commit()


def print_doctors(service: AppointmentService) -> None:
    keyword = input("Search by name/specialization (or Enter for all): ")
    doctors = service.doctors(keyword)
    if not doctors:
        print("No doctors found.")
    for doctor in doctors:
        print(f"ID {doctor.doctor_id} - {doctor.description()}")


def main() -> None:
    database = Database()
    database.setup()
    service = AppointmentService(database)
    print("\n=== Doctor Appointment Booking System ===")
    try:
        while True:
            print("\n1. Add doctor  2. View doctors  3. Book  4. View appointments  5. Cancel  6. Exit")
            choice = input("Choose: ").strip()
            try:
                if choice == "1":
                    service.add_doctor(input("Doctor name: "), input("Specialization: "),
                                       float(input("Consultation fee: ")))
                    print("Doctor added.")
                elif choice == "2":
                    print_doctors(service)
                elif choice == "3":
                    print_doctors(service)
                    appointment_id = service.book(
                        int(input("Doctor ID: ")), input("Patient name: "), input("Phone: "),
                        input("Email (optional): "), input("Date/time (YYYY-MM-DD HH:MM): "),
                    )
                    print(f"Appointment booked. ID: {appointment_id}")
                elif choice == "4":
                    phone = input("Patient phone (or Enter for all): ")
                    results = service.appointments(phone)
                    print(*results, sep="\n") if results else print("No appointments found.")
                elif choice == "5":
                    service.cancel(int(input("Appointment ID to cancel: ")))
                    print("Appointment cancelled.")
                elif choice == "6":
                    print("Goodbye!")
                    break
                else:
                    print("Please choose 1 to 6.")
            except (ValueError, sqlite3.Error) as error:
                print(f"Error: {error}")
    finally:
        database.close()


if __name__ == "__main__":
    main()
