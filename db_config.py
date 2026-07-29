"""
وحدة الاتصال وحفظ البيانات في قاعدة بيانات MySQL (مشروع إتقان - etgan)
"""

import json
from datetime import datetime
import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "etgan",
    "charset": "utf8mb4",
}


def get_connection():
    """إنشاء اتصال مع قاعدة البيانات"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"[X] خطأ في الاتصال بقاعدة البيانات: {e}")
        return None


def save_etimad_tender(tender):
    """حفظ أو تحديث مناقصة في جدول etimad_tenders"""
    conn = get_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        query = """
        INSERT INTO etimad_tenders (
            reference_number, name, agency, type, activity,
            publish_date, offer_deadline, opening_date, inquiry_deadline,
            doc_price, detail_url, raw_data, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            agency = VALUES(agency),
            type = VALUES(type),
            activity = VALUES(activity),
            publish_date = VALUES(publish_date),
            offer_deadline = VALUES(offer_deadline),
            opening_date = VALUES(opening_date),
            inquiry_deadline = VALUES(inquiry_deadline),
            doc_price = VALUES(doc_price),
            detail_url = VALUES(detail_url),
            raw_data = VALUES(raw_data),
            updated_at = VALUES(updated_at);
        """

        ref_no = tender.get("reference") or tender.get("id")
        raw_json = json.dumps(tender, ensure_ascii=False)

        values = (
            ref_no,
            tender.get("name", ""),
            tender.get("agency", ""),
            tender.get("type", ""),
            tender.get("activity", ""),
            tender.get("publish_date", ""),
            tender.get("offer_deadline", ""),
            tender.get("opening_date", ""),
            tender.get("inquiry_deadline", ""),
            tender.get("doc_price", ""),
            tender.get("detail_url", ""),
            raw_json,
            now,
            now,
        )

        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error as e:
        print(f"[X] خطأ حفظ مناقصة اعتماد في قاعدة البيانات: {e}")
        if conn.is_connected():
            conn.close()
        return False


def save_future_project(project):
    """حفظ أو تحديث مشروع مستقبلي في جدول future_projects"""
    conn = get_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        query = """
        INSERT INTO future_projects (
            project_id, name, agency, quarter, year, status, raw_data, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            agency = VALUES(agency),
            quarter = VALUES(quarter),
            year = VALUES(year),
            status = VALUES(status),
            raw_data = VALUES(raw_data),
            updated_at = VALUES(updated_at);
        """

        pid = project.get("id")
        raw_json = json.dumps(project, ensure_ascii=False)

        values = (
            pid,
            project.get("name", ""),
            project.get("agency", ""),
            project.get("quarter", ""),
            project.get("year", ""),
            project.get("status", ""),
            raw_json,
            now,
            now,
        )

        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error as e:
        print(f"[X] خطأ حفظ مشروع مستقبلي في قاعدة البيانات: {e}")
        if conn.is_connected():
            conn.close()
        return False


def save_qualification(qual):
    """حفظ أو تحديث دعوة تأهيل في جدول qualifications"""
    conn = get_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        query = """
        INSERT INTO qualifications (
            reference_number, name, agency, type, publish_date,
            inquiry_deadline, submission_deadline, evaluation_date,
            detail_url, raw_data, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            agency = VALUES(agency),
            type = VALUES(type),
            publish_date = VALUES(publish_date),
            inquiry_deadline = VALUES(inquiry_deadline),
            submission_deadline = VALUES(submission_deadline),
            evaluation_date = VALUES(evaluation_date),
            detail_url = VALUES(detail_url),
            raw_data = VALUES(raw_data),
            updated_at = VALUES(updated_at);
        """

        ref_no = qual.get("reference") or qual.get("id")
        raw_json = json.dumps(qual, ensure_ascii=False)

        values = (
            ref_no,
            qual.get("name", ""),
            qual.get("agency", ""),
            qual.get("type", ""),
            qual.get("publish_date", ""),
            qual.get("inquiry_deadline", ""),
            qual.get("submission_deadline", ""),
            qual.get("evaluation_date", ""),
            qual.get("detail_url", ""),
            raw_json,
            now,
            now,
        )

        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error as e:
        print(f"[X] خطأ حفظ دعوة تأهيل في قاعدة البيانات: {e}")
        if conn.is_connected():
            conn.close()
        return False


def save_supplier(supplier):
    """حفظ أو تحديث مورد في جدول suppliers"""
    conn = get_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        query = """
        INSERT INTO suppliers (
            supplier_id, name, cr_number, activity, city, phone, email, raw_data, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            cr_number = VALUES(cr_number),
            activity = VALUES(activity),
            city = VALUES(city),
            phone = VALUES(phone),
            email = VALUES(email),
            raw_data = VALUES(raw_data),
            updated_at = VALUES(updated_at);
        """

        sid = supplier.get("id") or supplier.get("cr_number") or supplier.get("name")
        raw_json = json.dumps(supplier, ensure_ascii=False)

        values = (
            sid,
            supplier.get("name", ""),
            supplier.get("cr_number", ""),
            supplier.get("activity", ""),
            supplier.get("city", ""),
            supplier.get("phone", ""),
            supplier.get("email", ""),
            raw_json,
            now,
            now,
        )

        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error as e:
        print(f"[X] خطأ حفظ مورد في قاعدة البيانات: {e}")
        if conn.is_connected():
            conn.close()
        return False
