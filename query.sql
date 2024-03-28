SELECT t4.fullname as Name,t4.mobile,t5.name as course,t1.bill_amount,t1.created_at
	FROM public.paymentrecords t1
INNER JOIN public.student t2 ON t1.student_id=t2.id
INNER JOIN public.studentchoices t3 ON t3.payment_id=t1.id
INNER JOIN public.student t4 ON t1.student_id=t4.id
INNER JOIN public.course t5 ON t5.id=t3.course_id
WHERE t1.created_at>'2022-03-31 23:59:12.944269+05:30' AND t1.created_at<'2023-04-01 00:21:52.001651+05:30'
ORDER BY t1.created_at

*************************

SELECT t2.fullname as Name,t2.mobile,t5.name as course,t3.expiry_date as Expiry_date
FROM public.student t2 
INNER JOIN public.studentchoices t3 ON t3.student_id=t2.id
INNER JOIN public.course t5 ON t5.id=t3.course_id
WHERE t3.course_id IN ('c609d956-efe7-4f44-b0aa-ab556a40ad75') 
AND t3.expiry_date>'2023-07-29 23:59:12.944269+05:30' order by t5.name 

=================================================================


SELECT t4.name as course, t5.name as category,t6.name as topic, t1.title
	FROM public.coursecategorylectures t1
INNER JOIN public.CategoryTopics t2 ON t1.category_topic_id=t2.id
INNER JOIN public.CourseCategories t3 ON t2.category_id=t3.id
INNER JOIN public.Course t4 ON t3.course_id=t4.id
INNER JOIN public.Category t5 ON t3.category_id=t5.id
INNER JOIN public.Topics t6 ON t2.topic_id=t6.id
 where t1.mobile_video_url is NULL AND t1.video_360 is NULL;
