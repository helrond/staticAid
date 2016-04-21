module.exports = function(grunt) {

  // Project configuration.
  grunt.initConfig({
    clean: {
      all: ['collections/*.html', 'families/*.html', 'organizations/*.html', 'people/*.html', 'software/*.html', '!**/index.html']
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
            dest: 'build/_site/',
            skip_initial_build: true,
            verbose: true,
            incremental: true
        }
      },
      build: {
        options: {
          serve: false,
          src: 'build/page_data/',
          dest: 'build/site/',
          verbose: true
        }
      }
    }
  });

  grunt.loadNpmTasks('grunt-contrib-clean');
  grunt.loadNpmTasks('grunt-exec');
  grunt.loadNpmTasks('grunt-jekyll');

  grunt.registerTask('serve', ['jekyll:serve']);
  grunt.registerTask('build', ['clean:all', 'exec:makePages', 'jekyll:build']);
  grunt.registerTask('update', ['exec:updateJSON', 'clean:all', 'exec:makePages', 'jekyll:build']);
  grunt.registerTask('rebuild', ['exec:replaceJSON', 'clean:all', 'exec:makePages', 'jekyll:build']);

};
