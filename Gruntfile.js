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
      makePages: {
        command: 'static-aid-build',
        stdout: true,
        stderr: true
      }
    },
    jekyll: {
      serve: {
          options: {
            serve: true,
            dest: 'build/site',
            skip_initial_build: true,
            verbose: true,
            incremental: true
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

  grunt.registerTask('serve', ['jekyll:serve']);
  grunt.registerTask('build', ['exec:makePages', 'jekyll:build']);
  grunt.registerTask('update', ['exec:updateJSON', 'exec:makePages', 'jekyll:build']);
  grunt.registerTask('rebuild', ['exec:replaceJSON', 'exec:makePages', 'jekyll:build']);

};
