$(document).ready(function() {

    History.Adapter.bind(window,'statechange',function(){ // Note: We are using statechange instead of popstate
        var State = History.getState(); // Note: We are using History.getState() instead of event.state
        $.ajax({
            url: State.hash,
            dataType: 'json',
            success: function(json) {
                $('.table-wrapper').html(json['list_partial']);
                $('.pagination-wrapper').html(json['paginator_full_partial']);
                affixDetails();
            }
        });
    });

    $('.form-gemstone').change(function() {
        update_results();
    });

    // DETAILS
    affixDetails();
    
    $('body').on('click', '.table-gemstone tr', function() {
        $('.table-gemstone tr.active').removeClass('active');
        $(this).addClass('active');
        $('.table-gemstone-detail .active').removeClass('active').addClass('hide');
        $('#' + this.id + '-detail').addClass('active').removeClass('hide');
    });

    // UI WIDGETS
    $('#price_range').slider({
        range: true,
        min: PRICES[0],
        max: PRICES[1],
        values: [PRICES[0], PRICES[1]],
        step: 100,
        slide: function(event, ui) {
            $('#price_min_display').val(FormatCurrency(ui.values[0]));
            $('#price_max_display').val(FormatCurrency(ui.values[1]));
        },
        change: function(event, ui) {
            $('#price_min').val(ui.values[0]);
            $('#price_max').val(ui.values[1]);
            update_results();
        }
    });
    $('.price_display').change(function() {
        var price_min = $('#price_min_display').val();
        $('#price_min_display').val(FormatCurrency(price_min));
        //$('#price_min').val(Number(price_min.replace(/[^0-9\.]+/g,"")));
        
        var price_max = $('#price_max_display').val();
        $('#price_max_display').val(FormatCurrency(price_max));
        //$('#price_max').val(Number(price_max.replace(/[^0-9\.]+/g,"")));
        
        $('#price_range').slider({
            values: [Number(price_min.replace(/[^0-9\.]+/g,"")), Number(price_max.replace(/[^0-9\.]+/g,""))]
        });
    });
    $('#carat_weight_range').slider({
        range: true,
        min: CARAT_WEIGHTS[0],
        max: CARAT_WEIGHTS[1],
        values: [CARAT_WEIGHTS[0], CARAT_WEIGHTS[1]],
        step: .1,
        slide: function(event, ui) {
            $('#carat_weight_min_display').html(ui.values[0]);
            $('#carat_weight_max_display').html(ui.values[1]);
        },
        change: function(event, ui) {
            $('#carat_weight_min').val(ui.values[0]);
            $('#carat_weight_max').val(ui.values[1]);
            update_results();
        }
    });
    $('#color_range').slider({
        range: true,
        min: 68,
        max: 90,
        values: [68, 90],
        step: 1,
        slide: function(event, ui) {
            $('#color_min_display').html(String.fromCharCode(ui.values[0]));
            $('#color_max_display').html(String.fromCharCode(ui.values[1]));
        },
        change: function(event, ui) {
            $('#color_min').val(String.fromCharCode(ui.values[0]));
            $('#color_max').val(String.fromCharCode(ui.values[1]));
            update_results();
        }
    });
    $('#clarity_range').slider({
        range: true,
        min: 0,
        max: CLARITIES.length-1,
        values: [0, CLARITIES.length-1],
        step: 1,
        slide: function(event, ui) {
            $('#clarity_min_display').html(CLARITIES[ui.values[0]][1]);
            $('#clarity_max_display').html(CLARITIES[ui.values[1]][1]);
        },
        change: function(event, ui) {
            $('#clarity_min').val(CLARITIES[ui.values[0]][0]);
            $('#clarity_max').val(CLARITIES[ui.values[1]][0]);
            update_results();
        }
    });
    $('#cut_grade_range').slider({
        range: true,
        min: 0,
        max: GRADINGS.length-1,
        values: [0, GRADINGS.length-1],
        step: 1,
        slide: function(event, ui) {
            $('#cut_grade_min_display').html(GRADINGS[ui.values[0]][1]);
            $('#cut_grade_max_display').html(GRADINGS[ui.values[1]][1]);
        },
        change: function(event, ui) {
            $('#cut_grade_min').val(GRADINGS[ui.values[1]][0]);
            $('#cut_grade_max').val(GRADINGS[ui.values[0]][0]);
            update_results();
        }
    });
    $('#polish_range').slider({
        range: true,
        min: 0,
        max: GRADINGS.length-1,
        values: [0, GRADINGS.length-1],
        step: 1,
        slide: function(event, ui) {
            $('#polish_min_display').html(GRADINGS[ui.values[0]][1]);
            $('#polish_max_display').html(GRADINGS[ui.values[1]][1]);
        },
        change: function(event, ui) {
            $('#polish_min').val(GRADINGS[ui.values[1]][0]);
            $('#polish_max').val(GRADINGS[ui.values[0]][0]);
            update_results();
        }
    });
    $('#symmetry_range').slider({
        range: true,
        min: 0,
        max: GRADINGS.length-1,
        values: [0, GRADINGS.length-1],
        step: 1,
        slide: function(event, ui) {
            $('#symmetry_min_display').html(GRADINGS[ui.values[0]][1]);
            $('#symmetry_max_display').html(GRADINGS[ui.values[1]][1]);
        },
        change: function(event, ui) {
            $('#symmetry_min').val(GRADINGS[ui.values[1]][0]);
            $('#symmetry_max').val(GRADINGS[ui.values[0]][0]);
            update_results();
        }
    });

    // Display the values of the UI slider's handles and also store them in hidden inputs for use with querying the server to refresh the results
    $('#price_min_display').val(FormatCurrency($('#price_range').slider('values', 0)));
    $('#price_max_display').val(FormatCurrency($('#price_range').slider('values', 1)));
    $('#carat_weight_min_display').html($('#carat_weight_range').slider('values', 0));
    $('#carat_weight_max_display').html($('#carat_weight_range').slider('values', 1));
    $('#color_min_display').html(String.fromCharCode($('#color_range').slider('values', 0)));
    $('#color_max_display').html(String.fromCharCode($('#color_range').slider('values', 1)));
    $('#clarity_min_display').html(CLARITIES[$('#clarity_range').slider('values', 0)][1]);
    $('#clarity_max_display').html(CLARITIES[$('#clarity_range').slider('values', 1)][1]);
    $('#cut_grade_min_display').html(GRADINGS[$('#cut_grade_range').slider('values', 0)][1]);
    $('#cut_grade_max_display').html(GRADINGS[$('#cut_grade_range').slider('values', 1)][1]);
    $('#polish_min_display').html(GRADINGS[$('#polish_range').slider('values', 0)][1]);
    $('#polish_max_display').html(GRADINGS[$('#polish_range').slider('values', 1)][1]);
    $('#symmetry_min_display').html(GRADINGS[$('#symmetry_range').slider('values', 0)][1]);
    $('#symmetry_max_display').html(GRADINGS[$('#symmetry_range').slider('values', 1)][1]);

    $('#price_min').val($('#price_range').slider('values', 0));
    $('#price_max').val($('#price_range').slider('values', 1));
    $('#carat_weight_min').val($('#carat_weight_range').slider('values', 0));
    $('#carat_weight_max').val($('#carat_weight_range').slider('values', 1));
    $('#color_min').val(String.fromCharCode($('#color_range').slider('values', 0)));
    $('#color_max').val(String.fromCharCode($('#color_range').slider('values', 1)));
    $('#clarity_min').val(CLARITIES[$('#clarity_range').slider('values', 0)][0]);
    $('#clarity_max').val(CLARITIES[$('#clarity_range').slider('values', 1)][0]);
    $('#cut_grade_min').val(GRADINGS[$('#cut_grade_range').slider('values', 1)][0]);
    $('#cut_grade_max').val(GRADINGS[$('#cut_grade_range').slider('values', 0)][0]);
    $('#polish_min').val(GRADINGS[$('#polish_range').slider('values', 1)][0]);
    $('#polish_max').val(GRADINGS[$('#polish_range').slider('values', 0)][0]);
    $('#symmetry_min').val(GRADINGS[$('#symmetry_range').slider('values', 1)][0]);
    $('#symmetry_max').val(GRADINGS[$('#symmetry_range').slider('values', 0)][0]);
    
    // ADVANCED
    $('.filter-advanced-toggle a').on('click', function(e) {
        $('.filter-advanced').toggleClass('hide');
        e.preventDefault();
    });

    // PAGINATION
    $('.paginator_link').on('click', function() {
        update_results($(this).attr('href'));
        return false;
    });

});

function affixDetails() {
    var details = $('.detail-affix').height();
    var results = $('.table-gemstone').height();

    if (results > details) {
        var top = $('.table-gemstone').offset().top;
        var height = $('body').height();

        var affix = $('.detail-affix').affix({
            offset: {
                top: top,
                bottom: function() {
                    return height - (top + results);
                }
            }
        });
        affix.width(affix.parent().width());
        affix.css('position', 'relative');
    }
}

function update_results(url) {
    // Set some defaults
    if (url) {
        var href = url += "&" + $('.form-gemstone').serialize();
    } else {
        var url = DIAMOND_LIST_URL;
        var href = "?" + $('.form-gemstone').serialize(); 
    }

    History.pushState(null, null, href);

    return false;
}

// Properly formats currency values for USD
function FormatCurrency(num) {
    num = num.toString().replace(/\$|\,/g,'');
    if(isNaN(num))
    num = "0";
    sign = (num == (num = Math.abs(num)));
    num = Math.floor(num*100+0.50000000001);
    //cents = num%100;
    num = Math.floor(num/100).toString();
    //if(cents<10)
    //cents = "0" + cents;
    for (var i = 0; i < Math.floor((num.length-(1+i))/3); i++)
    num = num.substring(0,num.length-(4*i+3))+','+
    num.substring(num.length-(4*i+3));
    //return (((sign)?'':'-') + '$' + num + '.' + cents);
    return (((sign)?'':'-') + '$' + num);
}
