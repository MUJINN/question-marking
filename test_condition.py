subject_id = 'unknown'
question_id = '9438222'
print('subject_id =', repr(subject_id))
print('question_id =', repr(question_id))
print('subject_id and question_id =', subject_id and question_id)
print('条件检查结果:', bool(subject_id and question_id))
condition_check = subject_id \!= 'unknown' and question_id \!= 'unknown'
print('是否需要改为检查不等于unknown:', condition_check)
