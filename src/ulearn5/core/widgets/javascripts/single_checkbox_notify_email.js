$(document).ready(function() {

    $('select#form-widgets-type_notify').on('change', function()
    {   
        if (this.value == 'automatic') {
            $("#formfield-form-widgets-distribution_lists").hide();
        } else {
            $("#formfield-form-widgets-distribution_lists").show();
        }
    });    

    if ($('select#form-widgets-type_notify').val() == 'automatic'){        
        $("#formfield-form-widgets-distribution_lists").hide();
    } else {
        $("#form-widgets-type_notify select").val("manual").change();
        $("#formfield-form-widgets-distribution_lists").show();
    }      

    if ($("#form-widgets-notify_activity_via_mail-0").is(':checked')){
            $("#formfield-form-widgets-type_notify").show();
            if ($('select#form-widgets-type_notify').val() == 'automatic'){
                $("#formfield-form-widgets-distribution_lists").hide();
            } else {
                $("#formfield-form-widgets-distribution_lists").show();
            }                         
    } else{
            $("#formfield-form-widgets-type_notify").hide();
            $("#formfield-form-widgets-distribution_lists").hide();           
    }    

    $("#form-widgets-notify_activity_via_mail-0").change(function(){       
        if ($(this).is(':checked')){
            $("#formfield-form-widgets-type_notify").show();
            if ($('select#form-widgets-type_notify').val() == 'automatic'){
                $("#formfield-form-widgets-distribution_lists").hide();
            } else {
                $("#formfield-form-widgets-distribution_lists").show();
            }             
        } else{
            $("#formfield-form-widgets-type_notify").hide();
            $("#formfield-form-widgets-distribution_lists").hide();
        }                
    });
    
});
