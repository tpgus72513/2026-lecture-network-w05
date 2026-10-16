# Week 05 관찰

## Task 1 — 서브넷과 longest-prefix match
- /31은 두 주소 모두 호스트(RFC 3021), /32는 그 주소 하나로 돌려주며 둘 다 broadcast는 없다.
- `10.20.30.70`은 /8·/16·/24·/26 네 항목에 다 들고, 가장 긴 /26(lab-rack-2)이 이긴다.
- 같은 길이 충돌은 같은 prefix 중복뿐이라, next hop이 다르면 거부하고 처음 경로를 둔다.

## Task 2 — 나는 인터넷 어디에 있나
- 집은 NAT 1겹이다. traceroute hop 2가 내 공인 주소 `124.52.76.47`과 같은 /24라 공유기 WAN이 곧 공인이다.
- LTE 핫스팟에선 공인(LG U+→KT)·사설 주소가 다 바뀌었다. 사설은 DHCP 서버가, 공인은 바깥 NAT가 정한다.
- Discover 출발지는 `0.0.0.0`이다. 아직 주소가 없어 이것뿐이고, 서버도 모르니 목적지는 broadcast다.

## Task 3 — longest-prefix match를 빠르게
- 16-8-8 multibit trie를 골랐다. 메모리는 linear의 24배(18.4 MB), 속도는 2,316×, 오답 0이다.
- lookup은 경로 수와 무관하게 주소 폭÷stride, 즉 최대 3번의 list index에 비례한다.
- Python에선 해시가 더 빠르지만, 하드웨어는 최악이 32단계로 고정된 bit-walk를 pipeline으로 만든다.
