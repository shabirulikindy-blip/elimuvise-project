from django.db.models import Q

def get_previous_score(student):
    """
    Finds the student's previous score from their results.
    Looks for a Result object with 'previous' in the subject name or assessment name.
    If not found, falls back to the average of all results, or 60.0 as a default.
    """
    prev_result = student.results.filter(
        Q(subject__icontains='previous') | Q(assessment_name__icontains='previous')
    ).first()
    if prev_result:
        return prev_result.score

    # Fallback 1: Average of all results
    all_results = student.results.all()
    if all_results.exists():
        scores = [r.score for r in all_results]
        return sum(scores) / len(scores)

    # Fallback 2: General safe default
    return 60.0

def get_student_advisory_data(student):
    """
    Calculates rule-based academic advisory details for a student.
    Uses attendance_rate and previous_score.
    """
    attendance = student.attendance_rate
    prev_score = get_previous_score(student)

    # Classify state
    is_attendance_low = attendance < 80.0
    is_performance_weak = prev_score < 50.0

    if is_attendance_low and is_performance_weak:
        # High Risk
        risk_level = "High"
        badge_class = "danger"
        summary = f"Critical risk: low attendance ({attendance}%) combined with weak previous performance ({prev_score:.1f}) indicates severe academic struggle."

        # Student-facing
        student_data = {
            "risk_alert": "Urgent Warning: Your attendance and grades are significantly below target, placing you in a High Risk category.",
            "study_reminders": [
                "Create a strict study plan of at least 15 hours per week.",
                "Review missed class materials and assignments daily."
            ],
            "weekly_actions": [
                "Attend all classes this week without exception.",
                "Submit all outstanding or late assignments to your teachers.",
                "Schedule a 1-on-1 meeting with your academic advisor."
            ],
            "advisor_recommendation": "URGENT: Please meet with your advisor immediately to establish an academic recovery contract."
        }

        # Advisor-facing
        advisor_data = {
            "risk_level": "high",
            "concerns": [
                f"Low attendance rate ({attendance}%)",
                f"Weak prior performance (Score: {prev_score:.1f})"
            ],
            "strengths": [
                "Opportunity to reset study habits with structured guidance"
            ],
            "interventions": [
                "Schedule urgent parent-teacher-advisor meeting.",
                "Implement a weekly attendance check-in.",
                "Enlist student in daily peer tutoring or homework club."
            ]
        }

        # Parent-facing
        parent_data = {
            "simplified_status": "Requires Urgent Intervention",
            "simplified_alert": "Urgent Notice: Your child's attendance is low, and academic performance needs immediate support.",
            "home_actions": [
                "Ensure your child leaves for school on time every day.",
                "Dedicate a quiet space for 2 hours of home study each evening.",
                "Contact the school advisor immediately to coordinate a support plan."
            ]
        }

    elif is_attendance_low and not is_performance_weak:
        # Medium Risk
        risk_level = "Medium"
        badge_class = "warning"
        summary = f"Moderate risk: stable prior performance ({prev_score:.1f}) but attendance is low ({attendance}%)."

        student_data = {
            "risk_alert": f"Attendance Alert: Your attendance ({attendance}%) is below the 80% target, which may soon cause your grades to drop.",
            "study_reminders": [
                "Catch up on notes for any class hours you have missed.",
                "Ensure you complete all assignments even if you miss a session."
            ],
            "weekly_actions": [
                "Aim for 100% attendance this week.",
                "Collect notes for any missed lectures from classmates.",
                "Check in briefly with your advisor to discuss attendance concerns."
            ],
            "advisor_recommendation": "Highly Recommended: Discuss any personal or transport hurdles with your advisor to keep attendance on track."
        }

        advisor_data = {
            "risk_level": "medium",
            "concerns": [
                f"Low attendance rate ({attendance}%) placing academic progress at risk."
            ],
            "strengths": [
                f"Strong academic foundation (Previous Score: {prev_score:.1f})"
            ],
            "interventions": [
                "Discuss attendance barriers with the student.",
                "Monitor attendance closely over the next two weeks.",
                "Inform parent of the attendance warning status."
            ]
        }

        parent_data = {
            "simplified_status": "Attendance Warning",
            "simplified_alert": "Attendance Notice: Your child has a solid academic base, but attendance has dropped below target.",
            "home_actions": [
                "Discuss the importance of consistent attendance with your child.",
                "Confirm that transport and health issues are not causing absences.",
                "Monitor attendance updates regularly."
            ]
        }

    elif not is_attendance_low and is_performance_weak:
        # Medium Risk
        risk_level = "Medium"
        badge_class = "warning"
        summary = f"Moderate risk: consistent attendance ({attendance}%) but prior performance is weak ({prev_score:.1f})."

        student_data = {
            "risk_alert": f"Academic Alert: Your attendance is great ({attendance}%), but your scores show room for improvement.",
            "study_reminders": [
                "Focus on core concepts in your weakest subjects.",
                "Increase self-study hours and practice past papers."
            ],
            "weekly_actions": [
                "Ask subject teachers for extra guidance on topics you found difficult.",
                "Form a study group with classmates who excel in these areas.",
                "Use the library or online study resources for at least 5 hours this week."
            ],
            "advisor_recommendation": "Recommended: Meet your advisor to review study habits and tutoring options."
        }

        advisor_data = {
            "risk_level": "medium",
            "concerns": [
                f"Weak prior performance (Score: {prev_score:.1f})"
            ],
            "strengths": [
                f"Excellent attendance record ({attendance}%) showing diligence and interest."
            ],
            "interventions": [
                "Review student's study methods and time allocation.",
                "Connect the student with peer tutors or school remedial classes.",
                "Provide extra practice materials for weak subjects."
            ]
        }

        parent_data = {
            "simplified_status": "Academic Support Recommended",
            "simplified_alert": "Academic Notice: Your child attends school regularly but is facing difficulties with core subjects.",
            "home_actions": [
                "Encourage your child to ask teachers questions when they don't understand.",
                "Support them in finding extra study time at home.",
                "Review academic goals and study habits together."
            ]
        }

    else:
        # Low Risk
        risk_level = "Low"
        badge_class = "success"
        summary = f"Low risk: good attendance ({attendance}%) and strong prior performance ({prev_score:.1f})."

        student_data = {
            "risk_alert": "Excellent Standing: You are performing well with stable attendance and grades.",
            "study_reminders": [
                "Maintain your current study routine and consistency.",
                "Challenge yourself with advanced practice questions."
            ],
            "weekly_actions": [
                "Offer help/tutoring to a classmate in a subject you excel in.",
                "Keep up the 100% effort in all upcoming quizzes.",
                "Explore enrichment activities or career goals."
            ],
            "advisor_recommendation": "Optional: Check in with your advisor periodically to discuss long-term academic plans."
        }

        advisor_data = {
            "risk_level": "low",
            "concerns": [
                "No major academic or attendance concerns"
            ],
            "strengths": [
                f"High attendance rate ({attendance}%)",
                f"Strong academic performance (Score: {prev_score:.1f})"
            ],
            "interventions": [
                "Encourage student to take on mentoring or peer tutoring roles.",
                "Explore enrichment materials and college readiness options."
            ]
        }

        parent_data = {
            "simplified_status": "Excellent Standing",
            "simplified_alert": "Progress Update: Your child has strong academic standing and consistent attendance. Keep encouraging them!",
            "home_actions": [
                "Praise your child for their hard work and dedication.",
                "Continue supporting their learning environment.",
                "Discuss their future academic and career aspirations."
            ]
        }

    return {
        "risk_level": risk_level,
        "badge_class": badge_class,
        "summary": summary,
        "prev_score": prev_score,
        "attendance": attendance,
        "student_data": student_data,
        "advisor_data": advisor_data,
        "parent_data": parent_data
    }

def prioritize_students(students_queryset):
    """
    Takes a Student queryset, computes advisory metrics, and sorts them by risk priority.
    High Risk (At-Risk prediction) comes first, sub-sorted by lowest attendance and lowest performance.
    """
    student_list = []
    for student in students_queryset:
        advisory_data = get_student_advisory_data(student)
        student.advisory_data = advisory_data

        # Priority weight calculation:
        # High Risk (At-Risk prediction) -> weight 300
        # Medium Risk (Average prediction) -> weight 200
        # Low Risk (any other prediction) -> weight 100
        risk_weight = 100
        if student.prediction == 'At-Risk':
            risk_weight = 300
        elif student.prediction == 'Average':
            risk_weight = 200

        # Prioritize lower attendance rate and lower previous score
        attendance_val = 100.0 - min(max(student.attendance_rate, 0.0), 100.0)
        perf_val = 100.0 - min(max(advisory_data["prev_score"], 0.0), 100.0)

        student.priority_score = risk_weight + (attendance_val * 2.0) + perf_val
        student_list.append(student)

    # Sort descending by priority score
    student_list.sort(key=lambda s: s.priority_score, reverse=True)
    return student_list
