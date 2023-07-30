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
WHERE t3.course_id IN ('05c1c611-474d-4295-be03-9b69be3fe3a7','427a7d26-53d2-416c-97b5-4bebf5b76603',
'0a5c4ceb-df8b-4978-b242-22ca431f7667','b98be0b6-848a-4a1f-b61a-9b52bb9c69f8','ce99f0eb-63eb-4e8f-931f-022ea3d3b6c5') 
AND t3.expiry_date>'2023-07-29 23:59:12.944269+05:30' order by t5.name 