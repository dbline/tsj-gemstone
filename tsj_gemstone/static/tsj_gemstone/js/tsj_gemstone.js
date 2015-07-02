$(document).ready(function() {

    // Establish Variables
    var State = History.getState();
    // Log Initial State
    History.log('initial:', State.data, State.title, State.url);

    History.Adapter.bind(window,'statechange',function(){ // Note: We are using statechange instead of popstate
        var State = History.getState(); // Note: We are using History.getState() instead of event.state
        $.ajax({
            url: State.hash,
            dataType: 'json',
            success: function(json) {
                $('.section-gemstones').html(json['gemstones']);
                $('.section-pagination').html(json['pagination']);
                affixDetails();
            }
        });
    });

    $('#form-gemstone .no-range').change(function() {
        updateResults();
    });

    // DETAILS
    affixDetails();

    $('body').on('click', '.table-gemstone tr', function() {
        if ($(this).hasClass('hidden-xs') || $(this).hasClass('hidden-sm')) {
            $('.table-gemstone tr.active').removeClass('active');
            $(this).addClass('active');
            $('.table-gemstone-detail .active').removeClass('active').addClass('hide');
            $('#' + this.id + '-detail').addClass('active').removeClass('hide');
        }
    });

    $('.slider').on('change', function() {
        var id = $(this).attr('id');
        from = $(this).data("from");
        to = $(this).data("to");
        $('#id_' + id + '_0').val(from);
        $('#id_' + id + '_1').val(to);
    });

    // Price
    $('#price').on('change', function() {
        var id = $(this).attr('id');
        from = formatCurrency($(this).data("from"));
        to = formatCurrency($(this).data("to"));
        $('#id_' + id + '_0').val(from);
        $('#id_' + id + '_1').val(to);
    });

    updateCurrency($('#id_price_0'));
    updateCurrency($('#id_price_1'));

    $('#id_price_0').on('change', function() {
        updateCurrency($(this));
        num = $(this).val();
        num = num.toString().replace(/\$|\,/g,'');
        price_slider.update({from: num});
        updateResults();
    });

    $('#id_price_1').on('change', function() {
        updateCurrency($(this));
        num = $(this).val();
        num = num.toString().replace(/\$|\,/g,'');
        price_slider.update({to: num});
        updateResults();
    });

    // Carat Weight
    $('#id_carat_weight_0').on('change', function() {
        updateCaratWeight($(this));
        carat_weight_slider.update({from: $(this).val()});
        updateResults();
    });

    $('#id_carat_weight_1').on('change', function() {
        updateCaratWeight($(this));
        carat_weight_slider.update({to: $(this).val()});
        updateResults();
    });

    // ADVANCED
    $('.filter-advanced-toggle a').on('click', function(e) {
        $('.filter-advanced').toggleClass('hide');
        e.preventDefault();
    });

    // SORTING
    $('body').on('click', 'th a', function() {
        updateResults($(this).attr('href'));
        return false;
    });

    // PAGINATION
    $('body').on('click', '.paginator_link', function() {
        updateResults($(this).attr('href'));
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

function formatCaratWeight(num) {
    num = num.toString().replace(/\,/g,'.');
    if(isNaN(num)) num = "0";
    return parseFloat(Math.round(num * 100) / 100).toFixed(2);
}

function updateCaratWeight(element) {
    var carat_weight = formatCaratWeight(element.val());
    element.val(carat_weight);
}

function formatCurrency(num) {
    num = num.toString().replace(/\$|\,/g,'');
    if(isNaN(num)) num = "0";
    sign = (num == (num = Math.abs(num)));
    num = Math.floor(num*100+0.50000000001);
    num = Math.floor(num/100).toString();
    for (var i = 0; i < Math.floor((num.length-(1+i))/3); i++)
    num = num.substring(0,num.length-(4*i+3))+','+
    num.substring(num.length-(4*i+3));
    return (((sign)?'':'-') + '$' + num);
}

function updateCurrency(element) {
    var price = formatCurrency(element.val());
    element.val(price);
}

function updateResults(url) {
    // Set some defaults
    if (url) {
        var href = url += "&" + $('#form-gemstone').serialize();
    } else {
        var url = DIAMOND_LIST_URL;
        var href = "?" + $('#form-gemstone').serialize();
    }

    href = href.replace(/%24/g, '').replace(/%2C/g, '');

    History.pushState(null, null, href);
    return false;
}
