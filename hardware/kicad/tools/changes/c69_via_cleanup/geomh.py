import math
def ang(c,p,q):
    v1=(p[0]-c[0],p[1]-c[1]); v2=(q[0]-c[0],q[1]-c[1]); n1=math.hypot(*v1); n2=math.hypot(*v2)
    if n1<1e-6 or n2<1e-6: return 180
    return math.degrees(math.acos(max(-1,min(1,(v1[0]*v2[0]+v1[1]*v2[1])/(n1*n2)))))
def octs(a,c):
    dx=c[0]-a[0]; dy=c[1]-a[1]; adx,ady=abs(dx),abs(dy)
    if adx<1e-4 or ady<1e-4 or abs(adx-ady)<1e-4: return [[a,c]]
    d=min(adx,ady); sx=math.copysign(1,dx); sy=math.copysign(1,dy)
    m1=(round(a[0]+sx*d,4),round(a[1]+sy*d,4))            # diag first
    m2=(round(c[0]-sx*d,4),round(c[1]-sy*d,4))            # straight first
    return [[a,m1,c],[a,m2,c]]
