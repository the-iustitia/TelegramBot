import json
import os

def validate_question(q, seen_ids):
    errors = []

    if "question" not in q:
        errors.append("missing_question")

    if "answers" not in q or not isinstance(q["answers"], list):
        errors.append("invalid_answers")

    if "correct_answer" not in q:
        errors.append("missing_correct_answer")
    elif "answers" in q and q["correct_answer"] not in q["answers"]:
        errors.append("correct_answer_not_in_answers")

    if "id" not in q:
        q_id = None
        errors.append("missing_id")
    else:
        try:
            q_id = int(q["id"])
            if q_id in seen_ids:
                errors.append("duplicate_id")
            else:
                seen_ids.add(q_id)
        except:
            q_id = None
            errors.append("non_numeric_id")

    return errors, q_id

def load_questions_from_folder(folder_path):
    questions = []
    file_map = {}
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            full_path = os.path.join(folder_path, filename)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        questions.extend(data)
                        for q in data:
                            file_map[q.get("id")] = filename
            except Exception as e:
                print(f"⚠️ Ошибка при чтении {filename}: {e}")
    return questions, file_map

def save_questions_to_file(path, questions):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.abspath(os.path.join(current_dir))  # /json
    questions_dir = os.path.join(base_dir, "questions")
    invalid_dir = os.path.join(base_dir, "invalid")
    os.makedirs(invalid_dir, exist_ok=True)

    all_questions, file_map = load_questions_from_folder(questions_dir)

    seen_ids = set()
    valid_questions = []
    invalid_questions = []

    next_id = 1
    for q in all_questions:
        if "id" not in q or not isinstance(q["id"], int):
            while next_id in seen_ids:
                next_id += 1
            q["id"] = next_id
        errors, q_id = validate_question(q, seen_ids)
        if errors:
            invalid_questions.append(q)
        else:
            valid_questions.append(q)

    valid_questions.sort(key=lambda x: x["id"])
    invalid_path = os.path.join(invalid_dir, "invalid_questions.json")
    save_questions_to_file(invalid_path, invalid_questions)

    questions_by_file = {}
    for q in valid_questions:
        file_name = file_map.get(q["id"])
        if file_name:
            questions_by_file.setdefault(file_name, []).append(q)

    for file_name, qs in questions_by_file.items():
        path = os.path.join(questions_dir, file_name)
        qs.sort(key=lambda x: x["id"])
        save_questions_to_file(path, qs)

    print(f"✅ Всего вопросов: {len(all_questions)}")
    print(f"✅ Валидных: {len(valid_questions)}")
    print(f"❌ Ошибочных: {len(invalid_questions)} — сохранены в {invalid_path}")

if __name__ == "__main__":
    main()