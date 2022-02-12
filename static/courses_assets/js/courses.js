function showSnackbar(message, status) {

  SnackBar({
    message: message,
    fixed: true,
    status: status,
    position: "tr" // bl, tl, tr, br
  });

}




document.getElementById('rzp-button1').onclick = function(e){
    
    product_id = document.getElementById('cart_subscription_id')
	data = {"product_id": product_id}
	fetch('/course/create_order/?create_order=True', {
	method: 'POST', // or 'PUT'
	body: JSON.stringify(data),// data can be `string` or {object}!
	headers:{
	  "Content-Type":"application/json"
	}
  })
  .then(res => res.json())
  .then(response => {
	
     if(response.status == true){
	  var options = {
	  "key": "{{ razorpay_key }}", // Enter the Key ID generated from the Dashboard
	  "amount": (response.amount)*100, // Amount is in currency subunits. Default currency is INR. Hence, 50000 refers to 50000 paise
	  "currency": "INR",
	  "name": "Imagnus",
	  "description": "Imagnus Study Material",
	  "image": "/static/courses_assets/img/imagnus-logo.jpg",
	  "order_id": response.order_id, //This is a sample Order ID. Pass the `id` obtained in the response of Step 1
	  "callback_url": "{{ app_url }}/student/my-purchases/",
	  "prefill": {
		  "name": "{{ student_name }}",
		  "email": "{{ email }}",
		  "contact": "{{ mobile }}"
	  },
	  "handler": function (response){
		  // alert(response.razorpay_payment_id);
		  // alert(response.razorpay_order_id);
		  // alert(response.razorpay_signature)
  
		  var data = {"payment_id": response.razorpay_payment_id,
					  "order_id":response.razorpay_order_id,
					  "signature":response.razorpay_signature
	  
			  }
  
		  fetch('/course/confirm_order/',{
			  method: 'POST',
			  body: JSON.stringify(data),
			  headers:{
				  "Content-Type":"application/json"
	}
		  })
		  .then((result) => {
			  return result.json();
		  }).then((res) => {
			  if(res.status == true){
				  showSnackbar(response.detail, "success")
				  setTimeout(() => {
					   window.location.href = res.redirectUrl
				  }, 3000);
				 
			  } else {
				  showSnackbar(response.message, "error")
			  }
			 
	  });
	  
	  },
	  "notes": {
		  "address": ""
	  },
	  "theme": {
		  "color": "#3399cc"
	  }
  };
	 } else {
		 alert("here")
				  showSnackbar(response.message, "error")
			  }
  
	  var rzp1 = new Razorpay(options);
	  rzp1.open();
	  e.preventDefault();

	  
  })
  .catch(error => console.error('Error:', error));
  
  
  
  
  }
  
		  /* razorpay ends */
