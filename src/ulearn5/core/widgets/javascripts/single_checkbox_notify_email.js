$(document).ready(function() {

    function eventsNotifyEmailCheckbox(checkField) {
        var communityForm = checkField.closest('form');
        if (checkField.is(':checked')){
            communityForm.find("#formfield-form-widgets-type_notify").show();
            if (communityForm.find('select#form-widgets-type_notify').val() == 'automatic'){
                communityForm.find("#formfield-form-widgets-distribution_lists").hide();
            } else {
                communityForm.find("#formfield-form-widgets-distribution_lists").show();
            }
        } else{
            communityForm.find("#formfield-form-widgets-type_notify").hide();
            communityForm.find("#formfield-form-widgets-distribution_lists").hide();
        }
    }

    function eventsNotifyEmailSelect(selectField) {
        var communityForm = selectField.closest('form');
        if (selectField.val() == 'automatic') {
            communityForm.find("#formfield-form-widgets-distribution_lists").hide();
        } else {
            communityForm.find("#formfield-form-widgets-distribution_lists").show();
        }
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

    if ($('select#form-widgets-type_notify').val() == 'automatic'){
        $("#formfield-form-widgets-distribution_lists").hide();
    } else {
        $("#form-widgets-type_notify select").val("manual").change();
        $("#formfield-form-widgets-distribution_lists").show();
    }

    $("input#form-widgets-notify_activity_via_mail-0").on('change', function(){
        eventsNotifyEmailCheckbox($(this));
    });

    $('select#form-widgets-type_notify').on('change', function() {
        eventsNotifyEmailSelect($(this));
    });

    $('#box_comunitats a[href=#addModal]').on('click', function() {
        setTimeout(function(){
           $("input#form-widgets-notify_activity_via_mail-0").on('change', function(){
                eventsNotifyEmailCheckbox($(this));
            });

            $('select#form-widgets-type_notify').on('change', function() {
                eventsNotifyEmailSelect($(this));
            });
        }, 500);
    });
});
