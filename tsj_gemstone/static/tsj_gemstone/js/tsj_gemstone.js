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
        if ($(this).hasClass('hidden-xs') || $(this).hasClass('hidden-sm')) {
            $('.table-gemstone tr.active').removeClass('active');
            $(this).addClass('active');
            $('.table-gemstone-detail .active').removeClass('active').addClass('hide');
            $('#' + this.id + '-detail').addClass('active').removeClass('hide');
        }
    });

    // FILTERS
    $(".slider").slider({tooltip: 'hide'});

    // ADVANCED
    $('.filter-advanced-toggle a').on('click', function(e) {
        $('.filter-advanced').toggleClass('hide');
        e.preventDefault();
    });

    // SORTING
    $('body').on('click', 'th a', function() {
        update_results($(this).attr('href'));
        return false;
    });

    // PAGINATION
    $('body').on('click', '.paginator_link', function() {
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
