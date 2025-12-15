"""
챗 기능 테스트 스크립트
서버 실행 후 이 스크립트로 챗 기능을 테스트할 수 있습니다.
"""

import requests
import json
import sys

BASE_URL = "http://localhost:3002"


def test_health():
    """Health Check 테스트"""
    print("=" * 60)
    print("1. Health Check")
    print("=" * 60)

    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 서버 상태: {data.get('status')}")
            print(
                f"✅ 사용 가능한 Provider: {', '.join(data.get('available_providers', []))}"
            )
            return True
        else:
            print(f"❌ 서버 응답 오류: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다.")
        print("   서버가 실행 중인지 확인하세요: python src/main.py")
        return False
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


def test_stream_chat():
    """스트리밍 챗 테스트"""
    print("\n" + "=" * 60)
    print("2. 스트리밍 챗 테스트")
    print("=" * 60)

    url = f"{BASE_URL}/api/chat/stream"
    data = {
        "query": "안녕하세요! 주식 투자 초보자에게 조언을 해주세요.",
        "messages": [],
    }

    try:
        print(f"\n질문: {data['query']}")
        print("\n응답:")
        print("-" * 60)

        response = requests.post(url, json=data, stream=True, timeout=30)

        if response.status_code != 200:
            print(f"❌ 오류: {response.status_code}")
            print(response.text)
            return False

        full_response = ""
        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    data_str = line_str[6:]  # 'data: ' 제거
                    try:
                        data_json = json.loads(data_str)
                        if data_json.get("done"):
                            print("\n" + "-" * 60)
                            print("✅ 스트리밍 완료")
                            return True
                        else:
                            content = data_json.get("content", "")
                            print(content, end="", flush=True)
                            full_response += content
                    except json.JSONDecodeError:
                        pass

        print("\n✅ 스트리밍 완료")
        return True

    except Exception as e:
        print(f"\n❌ 오류: {e}")
        return False


def test_chat():
    """일반 챗 테스트"""
    print("\n" + "=" * 60)
    print("3. 일반 챗 테스트")
    print("=" * 60)

    url = f"{BASE_URL}/api/chat"
    data = {"query": "삼성전자 주가에 대해 간단히 설명해줘", "messages": []}

    try:
        print(f"\n질문: {data['query']}")
        print("\n응답:")
        print("-" * 60)

        response = requests.post(url, json=data, timeout=30)

        if response.status_code != 200:
            print(f"❌ 오류: {response.status_code}")
            print(response.text)
            return False

        result = response.json()
        print(result.get("response", ""))
        print("\n" + "-" * 60)
        print(f"✅ 사용된 모델: {result.get('model', 'N/A')}")
        print(f"✅ 토큰 사용량: {result.get('usage', {}).get('tokens', 'N/A')}")
        return True

    except Exception as e:
        print(f"\n❌ 오류: {e}")
        return False


def test_models():
    """사용 가능한 모델 조회 테스트"""
    print("\n" + "=" * 60)
    print("4. 사용 가능한 모델 조회")
    print("=" * 60)

    url = f"{BASE_URL}/api/models"

    try:
        response = requests.get(url, timeout=5)

        if response.status_code != 200:
            print(f"❌ 오류: {response.status_code}")
            return False

        result = response.json()
        models = result.get("models", [])

        print(f"\n✅ 사용 가능한 모델: {len(models)}개")
        for model in models:
            print(
                f"   - {model.get('name', 'N/A')}: {model.get('display_name', 'N/A')}"
            )

        return True

    except Exception as e:
        print(f"\n❌ 오류: {e}")
        return False


def main():
    """메인 테스트 함수"""
    print("\n" + "=" * 60)
    print("🤖 InsightStock AI Service - 챗 기능 테스트")
    print("=" * 60)

    # Health Check
    if not test_health():
        print("\n❌ 서버가 실행되지 않았습니다.")
        print("   먼저 서버를 실행하세요: python src/main.py")
        sys.exit(1)

    # 챗 테스트
    results = []
    results.append(("스트리밍 챗", test_stream_chat()))
    results.append(("일반 챗", test_chat()))
    results.append(("모델 조회", test_models()))

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    for name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{name}: {status}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n🎉 모든 테스트 통과!")
    else:
        print("\n⚠️  일부 테스트 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
