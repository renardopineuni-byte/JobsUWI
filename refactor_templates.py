import os

template_dir = 'c:\\Users\\tudul\\IdeaProjects\\NewGravTest\\templates'
for fname in os.listdir(template_dir):
    if not fname.endswith('.html'): continue
    path = os.path.join(template_dir, fname)
    with open(path, 'r') as f:
        content = f.read()
    
    # job title -> role
    content = content.replace('job.title', 'job.role')
    content = content.replace('job_id', 'job.id') if 'approve_job(job_id' in content else content
    
    # interview slots
    content = content.replace('b.date_time', 'b.start')
    content = content.replace('b.interviewer_name', 'b.interviewer.username')
    content = content.replace('b.candidate_name', 'b.student.username')
    content = content.replace('b.slot_id', 'b.id')
    content = content.replace('slot.start_time', 'slot.start')
    
    # For UI titles, we might manually fix if needed, but the variables are key.
    
    with open(path, 'w') as f:
        f.write(content)
