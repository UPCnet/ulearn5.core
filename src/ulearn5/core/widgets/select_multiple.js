var field_data = {}
$.ajax({
    type: 'POST',
    url: 'selectMultipleData',
    success: function(data){
        field_data = $.parseJSON(data);
    }
});

var field_type = {}
$.ajax({
    type: 'POST',
    url: 'selectMultipleTypes',
    success: function(data){
        field_type = $.parseJSON(data);
    }
});

/*
var field_type = {
    'company_sector': false,
    'company_charge': false
}

var field_data = {
    'company_sector':
    [
        {
            'value': '',
            'options': [
                {'value': ''},
                {'value': ''}
            ]
        },
        {
            'value': '',
            'options': [
                {'value': ''},
            ]
        }
    ],

    'company_charge':
    [
         {
            'value': '',
            'options': [
                {'value': ''},
                {'value': ''}
            ]
        },
        {
            'value': '',
            'options': [
                {'value': ''},
            ]
        }
    ]
};*/

$(document).ready(function() {

    setTimeout(function() {

    	/*
    	*  Renders First level options for every twolevel widget
    	*/
    	function renderSecondLevel(id, data, first_level, second_level_selected, multiple) {
            var options = '';

            var level2_options = _.find(data, function(option) {
                    return option.value == first_level;
                });

            if (level2_options) {
                _.each(level2_options.options, function(option) {
                    var selected = '';
                    if (_.contains(second_level_selected, option.value)) {
                        selected = ' selected="selected"';
                    }
                    options += '<option value="' + option.value + '" ' + selected + '">' + option.value + '</option>';
                });
            } else {
                var selected = '';
            }

            var html = '';
            if (_.size(options) > 0) {
                if (multiple) {
                    html = '<br/><select id="' + id + '" class="twolevel-widget list-field form-control level2" multiple="multiple" size="5" required>' +
                        options +
                        '</select>';
                } else {
                    html = '<br/><select id="' + id + '" class="twolevel-widget list-field form-control level2" size="5" required>' +
                        options +
                        '</select>';
                }
            }
            $(id).html(html);
    	}

        /*
    	*  Renders selects on user interactions
    	*  Generates needed fields for z3c form fields
        */

        $('.twolevel-widget').each(function(index, element) {
            // Find the field wrapper for each twolevel select element
            var $level1_select = $(element);
            var second_level_id = "#" + $level1_select.attr('data-next');
            if (element.parentElement) {
                var level1_container = element.parentElement;
                var field_container = level1_container.parentElement;
                var fieldname = $level1_select.attr('data-fieldname');
        		var data = field_data[fieldname];

        		// Get the currently stored selected values if any
                var stored_first_level = $('.' + $level1_select.attr('id') + '-firstLevel').val();
                var stored_second_level = _.map($('.' + $level1_select.attr('id') + '-secondLevel'), function(value, key) {return $(value).val()});

                // Render the first level
                var options = '';

                _.each(data, function(option) {
                    var selected = '';
                    if (option.value === stored_first_level) {
                        selected = ' selected="selected"';
                    }

                    options += '<option value="' + option.value + '" ' + selected + '>' + option.value + '</option>';
                });

                $level1_select.html(options);

                if (stored_second_level.length > 0) {
                    renderSecondLevel(second_level_id, data, stored_first_level, stored_second_level, field_type[fieldname]);
                }

                //Save selected values
                var items = []
                var item
                if (stored_second_level.length > 0) {
                    _.each(stored_second_level, function(element, index, list) {
                        item = [];
                        item.push(stored_first_level);
                        item.push(element);
                        items.push(item);
                    });
                } else if (!stored_first_level == undefined) {
                    item = [];
                    item.push(stored_first_level);
                    items.push(item);
                }

                if (items.length > 0) {
                    $(field_container).find('input.twolevel-widget-value').remove();

                    _.each(items, function(element, index, list) {
                        var input_template = _.template('<input type="hidden" class="textarea-widget required tuple-field twolevel-widget-value" name="form.widgets.<%= fieldname %>.<%= index %>" id="form-widgets-<%= fieldname %>-<%= index %>" value="<%= value %>">');
                        var value = element.join('\n');
                        $(field_container).append(input_template({fieldname: fieldname, index: index, value: value}));
                    });
                    $(field_container).find('input[name="form.widgets.' + fieldname +'.count"]').val(items.length);
                }



        		// Trigger on selecting a item in any level
                $(field_container).on('change', '.twolevel-widget', function(event) {
                    //Find the selected first level value on data
                    var selected = $level1_select.val();
                    var level2_options = _.find(data, function(option) {
                        return option.value == selected;
                    });

                    var $current_select = $(event.currentTarget);
                    var is_second_level = $current_select.hasClass('level2');
                    var has_second_level = level2_options.options.length > 0;
                    var items = [];
                    var item;
        			// when clicking on first level
                    if (!is_second_level) {
                        // If second level has options, render the select
                        if (has_second_level) {
        					renderSecondLevel(second_level_id, data, selected, [], field_type[fieldname]);
                            $(second_level_id).focus();

                        // otherwise, save item as a only-one-level result, and remove second level select
                        } else {
                            $(second_level_id).find('select').remove();
                            item = [];
                            item.push(selected);
                            items.push([selected]);
                        }
                    } else {
                    // When clickin on a second level
                        var level2_selections = $current_select.val();
                        if(Array.isArray(level2_selections)){
                            _.each(level2_selections, function(element, index, list) {
                                item = [];
                                item.push(selected) ;
                                item.push(element);
                                items.push(item);
                            });
                        }else{
                            item = [];
                            item.push(selected) ;
                            item.push(level2_selections);
                            items.push(item);
                        }
                    }
                    // Clear previous hidden data and rebuild from current selections
                    $(field_container).find('input.twolevel-widget-value').remove();
                    _.each(items, function(element, index, list) {
                        var input_template = _.template('<input type="hidden" class="textarea-widget required tuple-field twolevel-widget-value" name="form.widgets.<%= fieldname %>.<%= index %>" id="form-widgets-<%= fieldname %>-<%= index %>" value="<%= value %>">');
                        var value = element.join('\n');
                        $(field_container).append(input_template({fieldname: fieldname, index: index, value: value}));
                    });
                    $(field_container).find('input[name="form.widgets.' + fieldname +'.count"]').val(items.length);

                });
            };
        });


        /*
    	*  Shows a popover with a description for every checkbox of the field
        */


        $('#form-widgets-interest_topics input')
        .on('mouseover', function(event) {
                var $select = $(event.target);
                var selectedfieldname = $select.val();
                var $objselected = _.find(list_interest_topics, function(field) {
                    return field.value === selectedfieldname;
                });

                /*var data = '<span>' + $objselected.description + '</span>';
                $("#" + $select.attr('data-content')).html(data);*/
                $select.attr('data-title', selectedfieldname);
                $select.attr('data-content', $objselected.description);
                $select.popover('show');
            }
        )
        .on('mouseout', function(event) {
            var $select = $(event.target);
            $select.popover('hide');
        });

    }, 1000);

});
