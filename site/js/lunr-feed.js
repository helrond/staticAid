// builds lunr
// (with gratitude to https://github.com/katydecorah/katydecorah.github.io/blob/master/js/lunr-feed.js and http://rayhightower.com/blog/2016/01/04/how-to-make-lunrjs-jekyll-work-together/)

var index = lunr(function () {
  this.field('title')
  this.field('url')
  this.field('record_type')
  this.field('creator')
  this.field('subjects')
  this.ref('href')
});

var search_data = $.getJSON("/search_data.json");
search_data.then(function(data) {
  $.each(data, function(i, value) {
    index.add(value);
  });
});

$(document).ready(function() {
  $('#search').submit(function(event) {
    event.preventDefault();
    var results = $('#results');
    var query = $('#query').val();
    var result = index.search(query);
    results.empty();
    results.prepend('<button type="button" class="btn-close close" aria-label="Close"></button><p>Found '+result.length+' result(s) for "'+query+'"</p>');
    result.forEach(function(result) {
      search_data.then(function(data) {
        var item = data[result.ref];
        results.append('<p><a href="'+item.url+'">'+item.title+'</a></p>');
      });
    });
    results.slideDown().fadeIn(200);
    // results.parent('.row').next('div').hide();
  });
  $('#results').on('click', 'button.btn-close', function(){
    $('#results').slideUp().fadeOut(200);
    $('#query').val('');
  });
});
