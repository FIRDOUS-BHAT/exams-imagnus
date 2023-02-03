SELECT t4.fullname as Name,t4.mobile,t5.name as course,t1.bill_amount,t1.created_at
	FROM public.paymentrecords t1
INNER JOIN public.student t2 ON t1.student_id=t2.id
INNER JOIN public.studentchoices t3 ON t3.payment_id=t1.id
INNER JOIN public.student t4 ON t1.student_id=t4.id
INNER JOIN public.course t5 ON t5.id=t3.course_id
WHERE t1.created_at>'2021-12-31 23:59:12.944269+05:30' AND t1.created_at<'2022-02-01 00:21:52.001651+05:30'
ORDER BY t1.created_at


select t5.slug as course,t4.slug as category FROM public.coursecategorylectures t2 
INNER JOIN public.categorytopics t1 on t1.id=t2.category_topic_id 
INNER JOIN public.coursecategories t3 ON t3.id=t1.category_id 
INNER JOIN public.category t4 on t4.id=t3.category_id 
INNER JOIN public.course t5 on t5.id=t3.course_id 
where t2.video_360 is not null;