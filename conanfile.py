from conans import ConanFile, CMake

class libD(ConanFile):
    name = "libD"
    version = "1.0"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    generators = "cmake"

    scm = {"type": "git",
           "url": "https://github.com/conan-ci-cd-training/libD.git",
           "revision": "auto"}

    def requirements(self):
        self.requires("libB/1.0@mycompany/stable")
        self.requires("libC/1.0@mycompany/stable")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.install()

    def package(self):
        self.copy("LICENSE", dst="licenses")

    def package_info(self):
        self.cpp_info.libs = ["libD",]
