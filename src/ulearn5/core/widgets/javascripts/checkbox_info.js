var checkbox_data = {}
$.ajax({
    type: 'POST',
    url: 'checkboxInfoData',
    success: function(data){
        checkbox_data = $.parseJSON(data);
    }
});

$(document).ready(function() {

    setTimeout(function() {

        $('div.checbox-info-widget').each(function() {
            var fieldname = $(this).attr('data-fieldname');
            var data = checkbox_data[fieldname];
            $(this).on('mouseover', 'input.checbox-info-widget', function(event) {
                var $select = $(event.target);
                var selectedfieldname = $select.val();
                var $objselected = _.find(data, function(field) {
                    return field.value === selectedfieldname;
                });
                $select.attr('data-title', selectedfieldname);
                $select.attr('data-content', $objselected.description);
                $select.popover('show');

            }).on('mouseout', function(event) {
                var $select = $(event.target);
                $select.popover('hide');
            });
        });

    }, 1000);

});
