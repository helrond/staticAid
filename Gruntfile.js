module.exports = function(grunt) {

  // Project configuration.
  grunt.initConfig({
    // pkg: grunt.file.readJSON('package.json'),
    clean: {
      collections: ['collections/*.html', '!collections/index.html']
    },
    exec: {
      updateJSON: {
        command: 'utilities/getJson.py --update',
        stdout: true,
        stderr: true
      },
      replaceJSON: {
        command: 'utilities/getJson.py --replace',
        stdout: true,
        stderr: true
      },
      makePages: {
        command: 'utilities/makePages.py',
        stdout: true,
        stderr: true
      }
    },
    jekyll: {
      serve: {
          options: {
          serve: true,
          skip_initial_build: true,
          verbose: true
        }
      },
      build: {
        options: {
          serve: false,
          verbose: true
        }
      }
    }
  });

  grunt.loadNpmTasks('grunt-contrib-clean');
  grunt.loadNpmTasks('grunt-exec');
  grunt.loadNpmTasks('grunt-jekyll');

  grunt.registerTask('serve', ['jekyll:serve']);
  grunt.registerTask('build', ['clean:collections', 'exec:makePages', 'jekyll:build']);
  grunt.registerTask('update', ['exec:updateJSON', 'clean:collections', 'exec:makePages', 'jekyll:build']);
  grunt.registerTask('rebuild', ['exec:replaceJSON', 'clean:collections', 'exec:makePages', 'jekyll:build']);

};
