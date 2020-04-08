
#include "libD/libD.h"

#include <iostream>
#include "libB/libB.h"
#include "libC/libC.h"


void hello_libD(int indent, const std::string& msg) {
    std::cout << std::string(indent, ' ') << "libD: " << msg << std::endl;    
    hello_libB(indent+1, "called from libD");
    hello_libC(indent+1, "called from libD");
}