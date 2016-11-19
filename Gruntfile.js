module.exports = function(grunt) {

  // Project configuration.
  grunt.initConfig({
    exec: {
      updateJSON: {
        command: 'static-aid-get-data --update',
        stdout: true,
        stderr: true
      },
      replaceJSON: {
        command: 'static-aid-get-data --replace',
        stdout: true,
        stderr: true
      },
      makePages_fullpage: {
        command: 'static-aid-build',
        stdout: true,
        stderr: true
      },
      makePages_embedded: {
          command: 'static-aid-build --embedded',
          stdout: true,
          stderr: true
      },
    },
    jekyll: {
      serve: {
          options: {
            serve: true,
            dest: 'build/site',
            skip_initial_build: true,
            verbose: true,
            no_watch: true
        }
      },
      build: {
        options: {
          serve: false,
          src: 'build/staging',
          dest: 'build/site',
          verbose: true
        }
      }
    }
  });

  grunt.loadNpmTasks('grunt-exec');
  grunt.loadNpmTasks('grunt-jekyll');

  if (grunt.option('embedded')) {
      var pageType = "embedded";
  }
  else {
      var pageType = "fullpage";
  }

  grunt.registerTask('serve', ['jekyll:serve']);
  grunt.registerTask('build', ['exec:makePages_' + pageType, 'jekyll:build']);
  grunt.registerTask('update', ['exec:updateJSON', 'exec:makePages_' + pageType, 'jekyll:build']);
  grunt.registerTask('rebuild', ['exec:replaceJSON', 'exec:makePages_' + pageType, 'jekyll:build']);
};
