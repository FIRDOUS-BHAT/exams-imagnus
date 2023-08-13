

      //prefixes of implementation that we want to test
      window.indexedDB = window.indexedDB || window.mozIndexedDB ||
         window.webkitIndexedDB || window.msIndexedDB;

      //prefixes of window.IDB objects
      window.IDBTransaction = window.IDBTransaction ||
         window.webkitIDBTransaction || window.msIDBTransaction;
      window.IDBKeyRange = window.IDBKeyRange || window.webkitIDBKeyRange ||
         window.msIDBKeyRange

      if (!window.indexedDB) {
         window.alert("Your browser doesn't support a stable version of IndexedDB.")
      }


      var db;
      var request = window.indexedDB.open("Imagnus", 1);
      
      request.onerror = function (event) {
         console.log("error: ");
      };

      request.onsuccess = function (event) {
         db = request.result;
         console.log("success: " + db);
      };

      request.onupgradeneeded = function (event) {
         var db = event.target.result;
         var objectStore = db.createObjectStore("test_series", { keyPath: "id",autoIncrement: true });


      }

// working with IndexDB

   function add(counter,chosen) {
      var request = db.transaction(["test_series"], "readwrite")
         .objectStore("test_series")
         .put({id:counter, name: chosen });

   }

    function readAllAns() {
         var state_arr = []
               var objectStore = db.transaction("test_series").objectStore("test_series");

               objectStore.openCursor().onsuccess = function (event) {
                  var cursor = event.target.result;

                  if (cursor) {
                     state_arr.push(cursor.value.name)

                  cursor.continue();

                  }

                  final_arr = JSON.stringify(state_arr)
                  console.log(final_arr)
                  $('#answer_state_data').val(final_arr)
                    var req = window.indexedDB.deleteDatabase("Imagnus");

                  $('#submit_test_series').submit()


               };

            }


      function removeStateAns() {
         var request = db.transaction(["test_series"], "readwrite")
            .objectStore("test_series")
            .delete();

         request.onsuccess = function (event) {
//            alert("Kenny's entry has been removed from your database.");
         };
      }
      // removeStateAns()

//Near checkboxes
//    var key = CryptoJS.enc.Base64.parse("#base64Key#");
//    var iv = CryptoJS.enc.Base64.parse("#base64IV#");

  $('.form-check-input').on('change', function() {
        $('.form-check-input').not(this).prop('checked', false);
    });
    $(document).on('click','#pref_submit_btn', function(){
         pref_slug = $('.form-check-input:checked').val()
		   if(pref_slug){
		     document.location.href='/student/courses/'+pref_slug+'/'
		   }else{
		     alert('preference not selected! ')
		   }

		})


		//timer
   var arr = []
$(document).on('click', '#submit_question', function(e){
  let chosen = $('[name="example1"]:checked').val()
   let callback = e.target.getAttribute('data-callback')


   if(typeof(chosen) === "undefined"){

      chosen = '';
   }

   url_split = callback.split('/')
   // console.log(url_split[8])
   add(parseInt(url_split[8])+1,chosen)
   arr.push(chosen)

   var text = JSON.stringify(arr);
   // var encrypted = CryptoJS.AES.encrypt(text, key, { iv: iv });
   // console.log(encrypted.toString());

   // localStorage.setItem("test_series_state", encrypted.toString())
   // const testState = localStorage.getItem('test_series_state')
   // var decrypted = CryptoJS.AES.decrypt(encrypted, key, { iv: iv });
   // console.log(decrypted.toString(CryptoJS.enc.Utf8));


   //  console.log(arr)
   function runsnackbar(message){
      SnackBar({
            message: message,
            status: "success",
            position: "bl" // bl, tl, tr, br
         });

}

          $.ajax({
                url: callback,
                type: "post", //Change this to post or put
                data: JSON.stringify({"chosen":chosen}),
                dataType: "json",
                contentType: "application/json",
                success: function(data) {
                  if(data.status){
                   $('#new_qsn_no').text(data.counter)
                   $('#new_qsn').text(data.qstn_content.qstn)
                   $('#opt_1_text').text(data.qstn_content.opt_1)
                   $('#opt_2_text').text(data.qstn_content.opt_2)
                   $('#opt_3_text').text(data.qstn_content.opt_3)
                   $('#opt_4_text').text(data.qstn_content.opt_4)
                  if(data.nx){
                     nx = data.nx
                  }else{
                     nx = null
                  }
                  $('#new_qsn_no').text(data.counter+1)
                  callback = '/student/submit/testSeriesQstns/'+data.cid+'/'+data.tid+'/'+data.qstn_content.id+'/'+nx+'/'+data.counter+'/'
                  $('#submit_question').attr('data-callback',callback)
                  $('input[name="example1"]').prop('checked', false);
                   }else{


                     SnackBar({
                        message: data.message,
                        fixed: true,
                        status: "error",
                        position: "tc" // bl, tl, tr, br
                     });

                      //alert(data.message)
                   }
                },
            });

})

$(document).on('click','#view_test',function(e) {
   
   let callback = e.target.getAttribute('data-callback')
   let no_qstns = $('#display_no_qstns').val()
   fetch(callback,{
      method: 'POST', // or 'PUT'
      headers: {
         'Content-Type': 'application/json',
      },

   })
   .then(response => response.json())
      .then(data => {
         console.log('Success:', data);
         if(data.status){
            const skipped = data.message.skipped
            $('#no_of_skipped').text(data.message.skipped)
            $('#no_of_attempted').text(data.message.attempted)
            $('#no_of_not_visited').text(parseInt(no_qstns)-(data.message.attempted+ data.message.skipped))
         }
      })
      .catch((error) => {
         console.error('Error:', error);
      });


})

$(document).on('click','.chat__message__dt', function(e) {
  let url = e.target.getAttribute('data-url');
  let title = e.target.getAttribute('data-title');

  if (url && title) {
    // Check if the URL ends with .mp4
    if (url.endsWith('.mp4')) {
      // Use the video tag
      $('#new_url').replaceWith('<video id="new_url" src="' + url + '" controls style="border: none; position: absolute; top: 0; height: 80%; width: 100%;" allowfullscreen controlsList="nodownload"></video>');
    } else if (url.endsWith('.m3u8')) {
      // Use the iframe
      $('#new_url').replaceWith('<iframe id="new_url" src="' + url + '" loading="lazy" style="border: none; position: absolute; top: 0; height: 100%; width: 100%;" allow="accelerometer; gyroscope; encrypted-media; picture-in-picture;" allowfullscreen="true"></iframe>');
    }
    $('#new_title').text(title);
  }
});


document.addEventListener('DOMContentLoaded', function() {
    let videoCards = document.querySelectorAll('.chat__message__dt');

    videoCards.forEach(card => {
        card.addEventListener('click', function() {
           let videoPath = this.getAttribute('data-url');
         //   alert(videoPath)
            let videoPlayer = document.getElementById('videoPlayer');
            let videoSrc = document.getElementById('videoSrc');
            
            videoSrc.src = videoPath;
            videoPlayer.load();
            videoPlayer.play();
        });
    });
});



   $('.chat__message__dt').click(function () {
      $('.chat__message__dt').removeClass('active');
      $(this).toggleClass('active');
   });


   $('.menu--link').click(function () {
      $('.menu--link').removeClass('active');
      $(this).toggleClass('active');
   });


let getTestSummary = () => {

   readAllAns()

   //  const testState = localStorage.getItem('test_series_state')
   //  console.log(testState)
   //  var decrypted = CryptoJS.AES.decrypt(testState, key, { iv: iv });
   // console.log(decrypted.toString(CryptoJS.enc.Utf8));
   // $('#submit_test_series').submit()
}

$('.submit_question').on('click', function (e) {
  let callback = e.target.getAttribute('data-callback');
  $('#submit_question').attr('data-callback',callback)
  $('#submit_question').trigger('click')
})

 document.addEventListener('contextmenu',
                        event => event.preventDefault());