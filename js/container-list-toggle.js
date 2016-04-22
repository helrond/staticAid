$(document).ready(function() {
  $('.container-list-toggle').click(function(event) {
    event.preventDefault();
    $(this).parent().children('.container-list').toggle();
    $(this).parent().toggleClass('expanded');
  });
});
