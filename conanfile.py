from conans import ConanFile, tools, AutoToolsBuildEnvironment, RunEnvironment
from conans.errors import ConanInvalidConfiguration
import os
import glob


class LibnameConan(ConanFile):
    name = "pulseaudio"
    version = "13.0"
    description = "PulseAudio is a sound system for POSIX OSes, meaning that it is a proxy for sound applications."
    topics = ("conan", "pulseaudio", "sound")
    url = "https://github.com/bincrafters/conan-pulseaudio"
    homepage = "http://pulseaudio.org/"
    license = "LGPL-2.1"

    generators = 'pkg_config'
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_alsa": [True, False],
        "with_glib": [True, False],
        "with_fftw": [True, False],
        "with_x11": [True, False],
        "with_openssl": [True, False],
        "with_dbus": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_alsa": True,
        "with_glib": True,
        "with_fftw": False,
        "with_x11": True,
        "with_openssl": True,
        "with_dbus": True,
    }
    
    build_requires = "gettext/0.20.1", "libtool/2.4.6"

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    _autotools = None

    def configure(self):
        if self.settings.compiler == "Visual Studio":
            raise ConanInvalidConfiguration("The project libsndfile can not be built by Visual Studio.")
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd


    def requirements(self):
        self.requires("libsndfile/1.0.30@")
        if self.options.with_alsa:
            self.requires("libalsa/1.1.9")
        if self.options.with_glib:
            self.requires("glib/2.67.0")
        if self.options.with_fftw:
            self.requires("fftw/3.3.8")
        if self.options.with_x11:
            self.requires("xorg/system")
        if self.options.with_openssl:
            self.requires("openssl/1.1.1h")   
        self.requires("libcap/2.45")

    def system_requirements(self):
        installer = tools.SystemPackageTool()
        if tools.os_info.with_apt:
            if self.options.with_dbus:
                installer.install('libdbus-1-dev')
        elif tools.os_info.with_yum or tools.os_info.with_dnf:
            if self.options.with_dbus:
                installer.install('dbus-devel')

    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        extracted_dir = self.name + "-" + self.version
        os.rename(extracted_dir, self._source_subfolder)

    def _configure_autotools(self):
        if not self._autotools:
            self._autotools = AutoToolsBuildEnvironment(self)
            args=[]
            for lib in ['alsa', 'x11', 'openssl', 'dbus']:
                args.append("--%s-%s" % ('enable' if getattr(self.options, 'with_' + lib) else 'disable', lib))
            args.append("--%s-glib2" % ('enable' if self.options.with_glib else 'disable'))
            args.append("--%s-fftw" % ('with' if self.options.with_fftw else 'without'))
            if self.options.shared:
                args.extend(['--enable-shared=yes', '--enable-static=no'])
            else:
                args.extend(['--enable-shared=no', '--enable-static=yes'])
            args.append("--with-udev-rules-dir=%s" % os.path.join(self.package_folder, "bin", "udev", "rules.d"))
            args.append("--disable-systemd-daemon")
            args.append("--disable-systemd-login")
            args.append("--disable-systemd-journal")
            with tools.environment_append({"PKG_CONFIG_PATH": self.build_folder}):
                with tools.environment_append({
                        "FFTW_CFLAGS": tools.PkgConfig("fftw").cflags,
                        "FFTW_LIBS": tools.PkgConfig("fftw").libs}) if self.options.with_fftw else tools.no_op():
                    self._autotools.configure(args=args,  configure_dir=self._source_subfolder)
        return self._autotools

    def build(self):
        if self.options.with_fftw:
            if self.options['fftw'].precision != "single":
                raise ConanInvalidConfiguration("pulseaudio needs fftw to be built with option fftw:precision=single")

        with tools.environment_append(RunEnvironment(self).vars):
            autotools = self._configure_autotools()
            autotools.make()

    def package(self):
        self.copy(pattern="LICENSE", dst="licenses", src=self._source_subfolder)
        with tools.environment_append(RunEnvironment(self).vars):
            autotools = self._configure_autotools()
            autotools.install()
        tools.rmdir(os.path.join(self.package_folder, 'etc'))
        tools.rmdir(os.path.join(self.package_folder, 'share'))
        tools.rmdir(os.path.join(self.package_folder, 'lib', 'cmake'))
        tools.rmdir(os.path.join(self.package_folder, 'lib', 'pkgconfig'))
        for f in glob.glob(os.path.join(self.package_folder, "lib", "**", "*.la"), recursive=True):
            os.remove(f)

    def package_info(self):
        self.cpp_info.libdirs = ['lib', os.path.join('lib', 'pulseaudio')]
        if self.options.with_glib:
            self.cpp_info.libs.append('pulse-mainloop-glib')
        self.cpp_info.libs.extend(['pulse-simple', 'pulse'])
        if not self.options.shared:
            self.cpp_info.libs.append('pulsecommon-%s' % self.version)
        if self.options.with_dbus:
            self.cpp_info.system_libs.append('dbus-1')
        self.cpp_info.defines = ['_REENTRANT']
        self.cpp_info.names['pkg_config'] = 'libpulse'
